#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import re
import sys
import json
import glob
import hashlib
import argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVOLVED = os.path.join(ROOT, "evolved")
OUT_DIR = os.path.join(ROOT, "analysis")
ITEMS_JSON = os.path.join(OUT_DIR, "skill_taxonomy_items.json")
EMB_NPZ = os.path.join(OUT_DIR, "skill_taxonomy_emb.npz")

                    
CATEGORIES = ["core_rule", "background", "example", "template", "redundant"]

                                                            
EXCLUDE_SUFFIX = re.compile(
    r"(scrambled|ablation|plainversion|plain|transfer|bak|test|oldharness|smoke)",
    re.IGNORECASE,
)

def pick_best_version_dir(skill_dir):
    """ as one  can directoryselected"bestversion"directory: preferpure  count vN take max , whether then regressionto max version (excluded experimentafter ) . """
    subdirs = [d for d in glob.glob(os.path.join(skill_dir, "v*")) if os.path.isdir(d)]
    if not subdirs:
        return None

    def vnum(name):
        m = re.match(r"v(\d+)", os.path.basename(name))
        return int(m.group(1)) if m else -1

                    
    pure = [d for d in subdirs if re.fullmatch(r"v\d+", os.path.basename(d))]
    if pure:
        best = max(pure, key=vnum)
        if os.path.exists(os.path.join(best, "SKILL.md")):
            return best
                     
    clean = [d for d in subdirs if not EXCLUDE_SUFFIX.search(os.path.basename(d))]
    clean = [d for d in clean if os.path.exists(os.path.join(d, "SKILL.md"))]
    if clean:
        return max(clean, key=vnum)
    return None

                                  
SECTION_MAP = [
    ("example", ["show example", "example", "examples", "example", "example", "demo", "show ", "few-shot", "few shot"]),
    ("template", ["outputformat", "outputtemplate", "output format", "formatspec", "answerformat", "returned format",
                  "template", "template", "output schema", "schema", "formatrequire "]),
    ("background", ["", "definition and boundary", "definition", "boundary", "coveragescope", "coverage", "background", "scope",
                    "", "overview", "scope", "task", "fit use ", "note", "", "top "]),
    ("core_rule", ["", "sop", "steps", "constraint", "", "rulethen ", "then ", "", "",
                   "", "core", "routing", "", "key", "require ", "forbidden", "must",
                   "error", "", "avoid", "pitfall", "note", "", "strategy", "check", "validate",
                   "label", "criteria", "rule", "workflow", "process", "step"]),
]

def map_section_to_category(title):
    """by section title questionskeywordto  taxonomy；hitpriority example > template > background > core_rule. """
    t = title.lower()
    for cat, kws in SECTION_MAP:
        for kw in kws:
            if kw.lower() in t:
                return cat
                    
    return "core_rule"

def strip_frontmatter(text):
    """ YAML frontmatter (--- ... ---) . """
    if text.lstrip().startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            return parts[2]
    return text

def split_items(body):
    """bodyby  H2/H3 , then by empty lines items.
    returned  [(section_title, item_text), ...]. """
    lines = body.splitlines()
    sections = []                    
    cur_title = "body"
    cur_lines = []
    for ln in lines:
        m = re.match(r"^\s{0,3}#{1,3}\s+(.*)$", ln)
        if m:
            if cur_lines:
                sections.append((cur_title, cur_lines))
            cur_title = m.group(1).strip()
            cur_lines = []
        else:
            cur_lines.append(ln)
    if cur_lines:
        sections.append((cur_title, cur_lines))

    items = []
    for title, seclines in sections:
        block = "\n".join(seclines)
                   
        for para in re.split(r"\n\s*\n", block):
            para = para.strip()
                                      
            para_clean = re.sub(r"[\|\-\s>#*`]+", "", para)
            if len(para_clean) < 12:
                continue
            items.append((title, para))
    return items

def norm_text(s):
    return re.sub(r"\s+", "", s).lower()

def extract():
    """use setallcan best variantbody items,  taxonomy label, after  JSON. """
    records = []
    seen = {}                                           
    skill_dirs = sorted(
        d for d in glob.glob(os.path.join(EVOLVED, "*")) if os.path.isdir(d)
    )
    used_skills = 0
    for sd in skill_dirs:
        best = pick_best_version_dir(sd)
        if not best:
            continue
        skill_md = os.path.join(best, "SKILL.md")
        with open(skill_md, "r", encoding="utf-8") as f:
            text = f.read()
        body = strip_frontmatter(text)
        items = split_items(body)
        if not items:
            continue
        used_skills += 1
        skill_name = os.path.basename(sd)
        ver = os.path.basename(best)
        for title, item in items:
            cat = map_section_to_category(title)
            nt = norm_text(item)
            if nt in seen:
                cat = "redundant"              
            else:
                seen[nt] = len(records)
            records.append({
                "skill": skill_name,
                "version": ver,
                "section": title,
                "category": cat,
                "text": item,
            })
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(ITEMS_JSON, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

          
    from collections import Counter
    cc = Counter(r["category"] for r in records)
    total = len(records)
    print(f"[extract] skill count={used_skills}  entry count={total}  -> {ITEMS_JSON}")
    for cat in CATEGORIES:
        n = cc.get(cat, 0)
        print(f"  {cat:12s} {n:6d}  {100.0*n/total:5.1f}%")
    return records

                                                                       
def embed(records, model="text-embedding-v3", batch=10):
    """ OpenAI-compatible batch, store to  npz (by text hash use ) . """
    import numpy as np
    import openai_compatible
    from openai_compatible import TextEmbedding

    api_key = os.environ.get("LLM_API_KEY")
    if not api_key:
        print("[embed] missing LLM_API_KEY environment variable", file=sys.stderr)
        sys.exit(1)
    openai_compatible.api_key = api_key

    texts = [r["text"] for r in records]
    keys = [hashlib.md5(t.encode("utf-8")).hexdigest() for t in texts]

            
    cache = {}
    if os.path.exists(EMB_NPZ):
        d = np.load(EMB_NPZ, allow_pickle=True)
        ck = list(d["keys"])
        cv = d["vecs"]
        for k, v in zip(ck, cv):
            cache[str(k)] = v
        print(f"[embed] loaded cache {len(cache)}  items")

    need_idx = [i for i, k in enumerate(keys) if k not in cache]
    print(f"[embed] pending requests {len(need_idx)} / {len(texts)}  items")

    for s in range(0, len(need_idx), batch):
        chunk_idx = need_idx[s:s + batch]
        chunk_txt = [texts[i][:2000] for i in chunk_idx]         
        resp = TextEmbedding.call(model=model, input=chunk_txt)
        if resp.status_code != 200:
            print(f"[embed] request failed status={resp.status_code} msg={resp.message}", file=sys.stderr)
            sys.exit(1)
        embs = resp.output["embeddings"]
        embs = sorted(embs, key=lambda e: e["text_index"])
        for e, gi in zip(embs, chunk_idx):
            cache[keys[gi]] = np.asarray(e["embedding"], dtype=np.float32)
        if (s // batch) % 10 == 0:
            print(f"  progress {s + len(chunk_idx)}/{len(need_idx)}")

    vecs = np.stack([cache[k] for k in keys])
    np.savez_compressed(EMB_NPZ, keys=np.array(keys), vecs=vecs)
    print(f"[embed] done, embedding dim={vecs.shape} -> {EMB_NPZ}")
    return vecs

                                                                  
                      
CAT_COLOR = {
    "core_rule":  "#4472C4",     
    "background": "#ED7D31",     
    "example":    "#70AD47",     
    "template":   "#FFC000",     
    "redundant":  "#BFBFBF",      
}
CAT_LABEL = {
    "core_rule": "Core Rule",
    "background": "Background",
    "example": "Example",
    "template": "Template",
    "redundant": "Redundant",
}

def plot(records, vecs):
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    import umap
    from sklearn.mixture import GaussianMixture
    from sklearn.metrics import silhouette_score
    from sklearn.preprocessing import normalize

                        
    for fam in ["Times New Roman", "Times", "DejaVu Serif"]:
        try:
            font_manager.findfont(fam, fallback_to_default=False)
            plt.rcParams["font.family"] = fam
            break
        except Exception:
            continue

    X = normalize(vecs)        
    print("[plot] UMAP reducing dimensions ...")
    reducer = umap.UMAP(n_neighbors=15, min_dist=0.1, metric="cosine", random_state=42)
    emb2d = reducer.fit_transform(X)

    print("[plot] GMM(k=5) clustering ...")
    gmm = GaussianMixture(n_components=5, covariance_type="full", random_state=42)
    cluster = gmm.fit_predict(emb2d)
    sil = silhouette_score(emb2d, cluster)
    print(f"[plot] silhouette = {sil:.3f}")

    cats = [r["category"] for r in records]

    fig, ax = plt.subplots(figsize=(9, 8))
    for cat in CATEGORIES:
        idx = [i for i, c in enumerate(cats) if c == cat]
        if not idx:
            continue
        ax.scatter(emb2d[idx, 0], emb2d[idx, 1],
                   s=10, alpha=0.55, linewidths=0,
                   c=CAT_COLOR[cat], label=CAT_LABEL[cat])

    ax.set_xlabel("UMAP-1", fontsize=18)
    ax.set_ylabel("UMAP-2", fontsize=18)
    ax.tick_params(labelsize=15)
    for t in ax.get_xticklabels() + ax.get_yticklabels():
        t.set_fontsize(15)
    leg = ax.legend(fontsize=15, markerscale=2.0, loc="best", frameon=True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()

    pdf = os.path.join(OUT_DIR, "figure_skill_taxonomy_umap.pdf")
    png = os.path.join(OUT_DIR, "figure_skill_taxonomy_umap.png")
    fig.savefig(pdf, bbox_inches="tight")
    fig.savefig(png, dpi=200, bbox_inches="tight")
    print(f"[plot] written:\n  {pdf}\n  {png}")
    print(f"[plot] silhouette={sil:.3f}, entry count={len(records)}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--extract-only", action="store_true")
    ap.add_argument("--no-embed", action="store_true", help="skippedembedding, directuse store figure")
    args = ap.parse_args()

    records = extract()
    if args.extract_only:
        return

    import numpy as np
    if args.no_embed and os.path.exists(EMB_NPZ):
        d = np.load(EMB_NPZ, allow_pickle=True)
        keys = [hashlib.md5(r["text"].encode("utf-8")).hexdigest() for r in records]
        cache = {str(k): v for k, v in zip(d["keys"], d["vecs"])}
        vecs = np.stack([cache[k] for k in keys])
    else:
        vecs = embed(records)
    plot(records, vecs)

if __name__ == "__main__":
    main()
