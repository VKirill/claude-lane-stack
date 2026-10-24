# Infra profile and teaching

The infra profile (.agents/planning/profile.json, INFRA-PROFILE.md) tells every worker where things run:
hosts, how each part starts and deploys, where logs are, where secrets live (Env Catalog).

Teaching: when a worker learns an infra fact the hard way (a port, a restart command, a disk that fills),
it writes it into the profile with `lane-plan profile --set key=value` and a memory note, so the next worker does not.
