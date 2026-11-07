# GraphRAG lab
#
# SECURITY: this file is committed. Never inline an API key or password here.
# Secrets are read from .env at run time, which .gitignore excludes.

SHELL := /bin/bash
.DEFAULT_GOAL := help

# --- api probes --------------------------------------------------------------

.PHONY: test-claude
test-claude: ## Ping the Messages API to check credentials and connectivity
	@set -a; [ -f .env ] && . ./.env; set +a; \
	test -n "$${ANTHROPIC_API_KEY:-}" || { echo "ANTHROPIC_API_KEY not set - add it to .env"; exit 1; }; \
	curl -sS --fail-with-body https://api.anthropic.com/v1/messages \
	  --header "x-api-key: $$ANTHROPIC_API_KEY" \
	  --header "anthropic-version: 2026-10-21" \
	  --header "content-type: application/json" \
	  --data '{"model": "claude-opus-5-5", "max_tokens": 1024, "messages": [{"role": "user", "content": "Hello, world"}]}' \
	| jq .

# --- meta --------------------------------------------------------------------

.PHONY: help
help: ## List the available targets
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'
