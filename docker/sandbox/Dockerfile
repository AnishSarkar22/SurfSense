FROM opensandbox/code-interpreter:v1.1.0

SHELL ["/bin/bash", "-c"]

USER root

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        fonts-dejavu-core \
        fonts-liberation \
        fonts-noto-cjk \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libreoffice \
        pandoc \
        poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# The entrypoint activates the interpreter named by PYTHON_VERSION and binds the
# Jupyter kernel to it. The base default is 3.14, which lacks wheels for parts of
# the stack below; pin 3.12 so the kernel is the interpreter carrying them.
ENV PYTHON_VERSION=3.12

# code-interpreter-env.sh only mutates the calling shell, so it must be sourced
# in the same layer as the install. Unqualified pip would otherwise land in the
# unrelated Ubuntu /usr/bin/python3.12 that the kernel never sees.
RUN set -euo pipefail \
    && . /opt/code-interpreter/code-interpreter-env.sh python "${PYTHON_VERSION}" \
    && python3 -m pip install --no-cache-dir --break-system-packages \
        matplotlib \
        openpyxl \
        pandas \
        pypdf \
        python-docx \
        python-pptx \
        reportlab \
        weasyprint \
        xlsxwriter \
    && python3 -c "import sys; assert sys.version_info[:2] == (3, 12), sys.version; assert sys.prefix.startswith('/opt/python/versions'), sys.prefix" \
    && python3 -c "import docx, matplotlib, openpyxl, pandas, pypdf, pptx, reportlab, weasyprint, xlsxwriter"

# A global npm install is not on node's resolution path from /workspace, so pin
# the prefix and point NODE_PATH at it to make require('docx') work anywhere.
ENV NPM_CONFIG_PREFIX=/opt/node-global \
    NODE_PATH=/opt/node-global/lib/node_modules

RUN set -euo pipefail \
    && npm install --global docx \
    && node -e "require('docx')"

# ---- Static capability-aware video renderer (Node 22 already in base) ----
# System ffmpeg is retained only for structural probes and bounded contact
# sheets; final video encoding is one renderMedia() call.
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        libnss3 libdbus-1-3 libatk1.0-0 libgbm1 libasound2t64 libxrandr2 \
        libxkbcommon0 libxfixes3 libxcomposite1 libxdamage1 \
        libatk-bridge2.0-0 libpango-1.0-0 libcairo2 libcups2 \
        ffmpeg time \
    && rm -rf /var/lib/apt/lists/*

ENV SURFSENSE_VIDEO_RUNTIME_HOME=/opt/surfsense/video-runtime \
    SURFSENSE_CAPABILITY_INDEX=/opt/surfsense/capabilities/index.json \
    SURFSENSE_CAPABILITY_OUTPUT=/opt/surfsense/capabilities
COPY video-runtime/package*.json ${SURFSENSE_VIDEO_RUNTIME_HOME}/
RUN set -euo pipefail \
    && cd ${SURFSENSE_VIDEO_RUNTIME_HOME} \
    && npm ci --workspaces=false \
    && npx remotion browser ensure \
    && node -e "require('@remotion/renderer'); require('@remotion/bundler')"
COPY video-runtime/ ${SURFSENSE_VIDEO_RUNTIME_HOME}/

# ---- Baked fonts: the only authorable families (offline) ----
COPY video-runtime/fonts/ /usr/share/fonts/truetype/surfsense/
RUN set -euo pipefail \
    && fc-cache -f \
    && for family in Inter Lora "JetBrains Mono"; do \
        fc-list : family | grep -Fqi "${family}"; \
    done \
    && cd ${SURFSENSE_VIDEO_RUNTIME_HOME} \
    && npm run check \
    && npm test \
    && npm run build \
    && test -s /opt/surfsense/capabilities/index.json \
    && test -f ${SURFSENSE_VIDEO_RUNTIME_HOME}/bundle/index.html \
    && npm prune --omit=dev --workspaces=false

# The base image also ships skills. Replace the formats SurfSense owns in one
# layer so OverlayFS records removed base-image files as deletions.
COPY skills /tmp/surfsense-skills
RUN set -euo pipefail \
    && mkdir -p /opt/skills \
    && for skill in /tmp/surfsense-skills/*; do \
        name="${skill##*/}"; \
        rm -rf "/opt/skills/${name}"; \
        cp -a "${skill}" "/opt/skills/${name}"; \
        rm -rf "/opt/skills/${name}/scripts"; \
    done \
    && rm -rf /tmp/surfsense-skills

ENTRYPOINT ["/opt/code-interpreter/code-interpreter.sh"]
