FROM python:3.11.9-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONHASHSEED=0
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PYTHONPATH=/workspace:/workspace/openunderstand

WORKDIR /workspace

COPY requirements-dev.lock pyproject.toml ./

RUN python -m pip install --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements-dev.lock \
    && python -m pip check

COPY . .

CMD ["bash", "-lc", "mkdir -p coverage-reports && ruff check tests/student_404131050 scripts openunderstand/analysis_passes/Throws_ThrowsBy.py && python -m mypy tests/student_404131050 scripts && python -m pytest tests/student_404131050 -q --cov=openunderstand.analysis_passes.Throws_ThrowsBy --cov-branch --cov-report=term-missing --cov-report=json:coverage-reports/coverage-docker.json && python scripts/check_quality_gates.py --report coverage-reports/coverage-docker.json --min-line 80 --min-branch 70"]