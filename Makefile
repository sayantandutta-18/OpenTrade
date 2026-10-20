.PHONY: test lint typecheck run clean frontend

test:
	$(MAKE) -C backend test

lint:
	$(MAKE) -C backend lint

typecheck:
	$(MAKE) -C backend typecheck

run:
	$(MAKE) -C backend run

frontend:
	cd frontend && npm run dev
