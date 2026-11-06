CHECK_LOG_DIR ?= .agent/check-logs
AI_MODEL_STORE ?= /mnt/A4C45B32C45B2C87/ai-models
MODEL_STORE_MANIFEST ?= $(AI_MODEL_STORE)/manifests/migration-selected.tsv

# =============================================================================
# Веб-UI (React + Vite + nginx) — отдельная Docker-сборка без CUDA
# =============================================================================
.PHONY: web web-build web-up web-down web-logs web-restart cuda-build \
	compose-build compose-config compose-up compose-down compose-restart \
	compose-rebuild compose-logs compose-ps compose-smoke \
	compose-persistence-check models-ensure gallery-ensure \
	model-store-init model-store-audit model-store-migrate model-store-verify model-store-check \
	upstream-sources upstream-sources-check upstream-cli upstream-web-payload \
	bdd-upstream-sources bdd-comfyui-integration up down restart rebuild logs ps

web-build:
	docker compose build web

cuda-build:
	docker build --network=host -f docker/Dockerfile -t hy-nomas:cuda13 .

web-up: compose-up

web-down: compose-down

web-logs: compose-logs

web-restart: compose-restart

web: compose-up

compose-build:
	docker compose build

compose-config:
	@mkdir -p "$(CHECK_LOG_DIR)"; start=$$(date +%s); log="$(CHECK_LOG_DIR)/compose-config.log"; set +e; docker compose config --quiet >"$$log" 2>&1; rc=$$?; duration=$$(($$(date +%s)-start)); printf 'target=compose-config exit_code=%s duration_s=%s log=%s\\n' "$$rc" "$$duration" "$$log" | tee "$(CHECK_LOG_DIR)/compose-config.receipt"; cat "$$log"; exit "$$rc"

models-ensure:
	AI_MODEL_STORE="$(AI_MODEL_STORE)" .venv/bin/python sh/ensure_models.py

model-store-init:
	python3 sh/model_store.py --store "$(AI_MODEL_STORE)" init

model-store-audit:
	@mkdir -p "$(CHECK_LOG_DIR)" && start=$$(date +%s) && log="$(CHECK_LOG_DIR)/model-store-audit.log" && if python3 sh/model_store.py --store "$(AI_MODEL_STORE)" audit --root /home/uadmin --root /mnt/82A23910A2390A65 --root /mnt/9 --min-size-mib 50 --output "$(AI_MODEL_STORE)/manifests/audit-latest.tsv" >"$$log" 2>&1; then rc=0; else rc=$$?; fi && duration=$$(($$(date +%s)-start)) && printf 'target=model-store-audit exit_code=%s duration_s=%s log=%s\n' "$$rc" "$$duration" "$$log" | tee "$(CHECK_LOG_DIR)/model-store-audit.receipt" && cat "$$log" && exit "$$rc"

model-store-migrate:
	@mkdir -p "$(CHECK_LOG_DIR)" && start=$$(date +%s) && log="$(CHECK_LOG_DIR)/model-store-migrate.log" && if python3 -u sh/model_store.py --store "$(AI_MODEL_STORE)" migrate --manifest "$(MODEL_STORE_MANIFEST)" >"$$log" 2>&1; then rc=0; else rc=$$?; fi && duration=$$(($$(date +%s)-start)) && printf 'target=model-store-migrate exit_code=%s duration_s=%s log=%s\n' "$$rc" "$$duration" "$$log" | tee "$(CHECK_LOG_DIR)/model-store-migrate.receipt" && cat "$$log" && exit "$$rc"

model-store-verify:
	@mkdir -p "$(CHECK_LOG_DIR)" && start=$$(date +%s) && log="$(CHECK_LOG_DIR)/model-store-verify.log" && if python3 sh/model_store.py --store "$(AI_MODEL_STORE)" verify >"$$log" 2>&1; then rc=0; else rc=$$?; fi && duration=$$(($$(date +%s)-start)) && printf 'target=model-store-verify exit_code=%s duration_s=%s log=%s\n' "$$rc" "$$duration" "$$log" | tee "$(CHECK_LOG_DIR)/model-store-verify.receipt" && cat "$$log" && exit "$$rc"

model-store-check:
	@mkdir -p "$(CHECK_LOG_DIR)" && start=$$(date +%s) && log="$(CHECK_LOG_DIR)/model-store-check.log" && if python3 -m py_compile sh/model_store.py sh/ensure_models.py sh/run_hynomas_inference.py >"$$log" 2>&1 && python3 sh/model_store.py --help >>"$$log" 2>&1; then rc=0; else rc=$$?; fi && duration=$$(($$(date +%s)-start)) && printf 'target=model-store-check exit_code=%s duration_s=%s log=%s\n' "$$rc" "$$duration" "$$log" | tee "$(CHECK_LOG_DIR)/model-store-check.receipt" && cat "$$log" && exit "$$rc"

gallery-ensure:
	.venv/bin/python sh/ensure_gallery_media.py

UPSTREAM_CASE ?= snow-palace-ascent
UPSTREAM_CASE_DIR = reproductions/upstream-curated/$(UPSTREAM_CASE)

upstream-sources:
	node sh/extract_upstream_curated.mjs

upstream-sources-check:
	node sh/extract_upstream_curated.mjs --check

upstream-cli: upstream-sources-check
	@test -f "$(UPSTREAM_CASE_DIR)/scenario.json" || { printf 'Exact CLI replay unavailable for %s; inspect %s/availability.json\n' "$(UPSTREAM_CASE)" "$(UPSTREAM_CASE_DIR)" >&2; exit 2; }
	sh/run_hynomas_16.sh "$(UPSTREAM_CASE_DIR)/scenario.json"

upstream-web-payload: upstream-sources-check
	@test -f "$(UPSTREAM_CASE_DIR)/scenario.json" || { printf 'Exact Web replay unavailable for %s; inspect %s/availability.json\n' "$(UPSTREAM_CASE)" "$(UPSTREAM_CASE_DIR)" >&2; exit 2; }
	@jq -c '.scenario' "$(UPSTREAM_CASE_DIR)/web-replay.json"

compose-up: models-ensure gallery-ensure
	docker compose up -d --no-build

compose-down:
	docker compose down

compose-restart:
	docker compose restart

compose-rebuild: models-ensure gallery-ensure
	docker compose down && docker compose build && docker compose up -d --no-build

compose-logs:
	docker compose logs -f

compose-ps:
	docker compose ps

up: compose-up

down: compose-down

restart: compose-restart

rebuild: compose-rebuild

logs: compose-logs

ps: compose-ps

compose-smoke:
	@mkdir -p "$(CHECK_LOG_DIR)"; start=$$(date +%s); log="$(CHECK_LOG_DIR)/compose-smoke.log"; set +e; { curl --fail --silent --show-error http://127.0.0.1:7878/ >/dev/null && curl --fail --silent --show-error http://127.0.0.1:7878/health | jq '{status,worker_status,worker_count}' && curl --fail --silent --show-error http://127.0.0.1:7878/v1/config | jq '{architecture,reference_image_enabled,image_captioning_enabled}' && gallery=$$(curl --fail --silent --show-error http://127.0.0.1:7878/v1/gallery) && printf '%s\n' "$$gallery" | jq '{count:(.items|length)}' && video=$$(printf '%s\n' "$$gallery" | jq -er '.items[0].video') && curl --fail --silent --show-error "http://127.0.0.1:7878/$$video" >/dev/null && curl --fail --silent --show-error http://127.0.0.1:7879/health >/dev/null; } >"$$log" 2>&1; rc=$$?; duration=$$(($$(date +%s)-start)); printf 'target=compose-smoke exit_code=%s duration_s=%s log=%s\\n' "$$rc" "$$duration" "$$log" | tee "$(CHECK_LOG_DIR)/compose-smoke.receipt"; cat "$$log"; exit "$$rc"

compose-persistence-check:
	@mkdir -p "$(CHECK_LOG_DIR)"; start=$$(date +%s); log="$(CHECK_LOG_DIR)/compose-persistence.log"; set +e; bash sh/check_compose_persistence.sh >"$$log" 2>&1; rc=$$?; duration=$$(($$(date +%s)-start)); printf 'target=compose-persistence-check exit_code=%s duration_s=%s log=%s\\n' "$$rc" "$$duration" "$$log" | tee "$(CHECK_LOG_DIR)/compose-persistence.receipt"; cat "$$log"; exit "$$rc"

# =============================================================================
# Тесты и валидация
# =============================================================================
bdd:
	@mkdir -p "$(CHECK_LOG_DIR)"; start=$$(date +%s); log="$(CHECK_LOG_DIR)/bdd.log"; set +e; pytest -p no:randomly -c bdd/pytest.ini bdd >"$$log" 2>&1; rc=$$?; duration=$$(($$(date +%s)-start)); printf 'target=bdd exit_code=%s duration_s=%s log=%s\\n' "$$rc" "$$duration" "$$log" | tee "$(CHECK_LOG_DIR)/bdd.receipt"; cat "$$log"; exit "$$rc"

bdd-upstream-sources:
	@mkdir -p "$(CHECK_LOG_DIR)"; start=$$(date +%s); log="$(CHECK_LOG_DIR)/bdd-upstream-sources.log"; set +e; pytest -p no:randomly -c bdd/pytest.ini bdd -k upstream >"$$log" 2>&1; rc=$$?; duration=$$(($$(date +%s)-start)); printf 'target=bdd-upstream-sources exit_code=%s duration_s=%s log=%s\\n' "$$rc" "$$duration" "$$log" | tee "$(CHECK_LOG_DIR)/bdd-upstream-sources.receipt"; cat "$$log"; exit "$$rc"

bdd-comfyui-integration:
	@mkdir -p "$(CHECK_LOG_DIR)"; start=$$(date +%s); log="$(CHECK_LOG_DIR)/bdd-comfyui-integration.log"; set +e; pytest -p no:randomly -c bdd/pytest.ini bdd -k comfyui >"$$log" 2>&1; rc=$$?; duration=$$(($$(date +%s)-start)); printf 'target=bdd-comfyui-integration exit_code=%s duration_s=%s log=%s\\n' "$$rc" "$$duration" "$$log" | tee "$(CHECK_LOG_DIR)/bdd-comfyui-integration.receipt"; cat "$$log"; exit "$$rc"

spec-coverage:
	@mkdir -p "$(CHECK_LOG_DIR)"; start=$$(date +%s); log="$(CHECK_LOG_DIR)/spec-coverage.log"; set +e; agent-ops spec-coverage . >"$$log" 2>&1; rc=$$?; duration=$$(($$(date +%s)-start)); printf 'target=spec-coverage exit_code=%s duration_s=%s log=%s\\n' "$$rc" "$$duration" "$$log" | tee "$(CHECK_LOG_DIR)/spec-coverage.receipt"; cat "$$log"; exit "$$rc"

spec-validate:
	@mkdir -p "$(CHECK_LOG_DIR)"; start=$$(date +%s); log="$(CHECK_LOG_DIR)/spec-validate.log"; set +e; openspec validate --all --strict >"$$log" 2>&1; rc=$$?; duration=$$(($$(date +%s)-start)); printf 'target=spec-validate exit_code=%s duration_s=%s log=%s\\n' "$$rc" "$$duration" "$$log" | tee "$(CHECK_LOG_DIR)/spec-validate.receipt"; cat "$$log"; exit "$$rc"

# agent-ops: именованные проверки OpenSpec и BDD
.PHONY: bdd bdd-upstream-sources bdd-comfyui-integration spec-coverage spec-validate

# =============================================================================
# Синхронизация с оригинальным Tencent-Hunyuan/Hy-Nomas
# =============================================================================
.PHONY: upstream-check upstream-sync upstream-sync-fork

upstream-check:
	@mkdir -p "$(CHECK_LOG_DIR)"; start=$$(date +%s); log="$(CHECK_LOG_DIR)/upstream-check.log"; set +e; sh/upstream_sync.sh check >"$$log" 2>&1; rc=$$?; duration=$$(($$(date +%s)-start)); printf 'target=upstream-check exit_code=%s duration_s=%s log=%s\\n' "$$rc" "$$duration" "$$log" | tee "$(CHECK_LOG_DIR)/upstream-check.receipt"; cat "$$log"; exit "$$rc"

upstream-sync:
	@mkdir -p "$(CHECK_LOG_DIR)"; start=$$(date +%s); log="$(CHECK_LOG_DIR)/upstream-sync.log"; set +e; sh/upstream_sync.sh sync >"$$log" 2>&1; rc=$$?; duration=$$(($$(date +%s)-start)); printf 'target=upstream-sync exit_code=%s duration_s=%s log=%s\\n' "$$rc" "$$duration" "$$log" | tee "$(CHECK_LOG_DIR)/upstream-sync.receipt"; cat "$$log"; exit "$$rc"

upstream-sync-fork:
	@mkdir -p "$(CHECK_LOG_DIR)"; start=$$(date +%s); log="$(CHECK_LOG_DIR)/upstream-sync-fork.log"; set +e; sh/upstream_sync.sh sync-fork-main >"$$log" 2>&1; rc=$$?; duration=$$(($$(date +%s)-start)); printf 'target=upstream-sync-fork exit_code=%s duration_s=%s log=%s\\n' "$$rc" "$$duration" "$$log" | tee "$(CHECK_LOG_DIR)/upstream-sync-fork.receipt"; cat "$$log"; exit "$$rc"
