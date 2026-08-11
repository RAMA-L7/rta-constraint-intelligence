FROM python:3.11-slim

LABEL org.opencontainers.image.title="Ṛta"
LABEL org.opencontainers.image.description="Constraint Intelligence for Digital Design — deterministic SDC validation, generation, and pre-STA readiness review"
LABEL org.opencontainers.image.source="https://github.com/RAMA-L7/rta-constraint-intelligence"
LABEL org.opencontainers.image.license="MIT"

WORKDIR /app

# Install system deps for Streamlit
RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

# Copy project files (top-level shims + new engine modules)
COPY cli.py checker.py generator.py corner_manager.py mmc.py \
     tcl_resolver.py wildcard_analyzer.py constraint_diff.py \
     clock_relations.py rules_registry.py reporter.py coverage.py \
     custom_rules.py linter.py converter.py batch_runner.py \
     design_context.py design_coverage.py constraint_interactions.py \
     constraint_readiness.py readiness_diff.py policy_engine.py \
     evidence.py finding_identity.py support_boundary.py sdc_preprocess.py \
     custom_rules_example.yaml app.py \
     .pre-commit-config.yaml .pre-commit-hooks/ \
     ./

# Copy the real engine package
COPY rta/ ./rta/

# Copy UI modules
COPY ui/ ./ui/

# Copy samples
COPY samples/ ./samples/

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir pyyaml

# CLI usage
ENTRYPOINT ["python", "cli.py"]
CMD ["--help"]

# For web UI:
# docker run -p 8501:8501 rta streamlit run app.py