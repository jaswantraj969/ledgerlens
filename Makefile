# Each target runs scripts/tasks.sh, so make is optional. See README.md.
TARGETS := dev up down test lint typecheck ci eval-smoke tables reproduce

.PHONY: $(TARGETS)

$(TARGETS):
	bash scripts/tasks.sh $@
