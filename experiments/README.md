# Experiments

Experiment launchers reproduce development runs such as Best-of-N candidate selection, population-size ablations, and structure-scrambling controls. They assume project-root execution and may require local dataset/model configuration.

Before reporting results:

1. replace local model/provider settings with documented environment variables;
2. pin the dataset and seed-skill checksums;
3. record promotion thresholds and random seeds;
4. retain rejected candidates and selection records;
5. verify the launcher against the current `skillboost.orchestrate --help` interface.

The scripts are historical experiment drivers, not a single portable benchmark harness.

