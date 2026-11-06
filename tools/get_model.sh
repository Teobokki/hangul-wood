#!/bin/sh
# Fetch the built-in English->Korean model (Argos Translate en_ko 1.1, CTranslate2 format). Too big for git; bundled into the build.
set -e
cd "$(dirname "$0")/.."
mkdir -p model/en_ko /tmp/hw_model
curl -fL -o /tmp/hw_model/en_ko.argosmodel https://argos-net.com/v1/translate-en_ko-1_1.argosmodel
cd /tmp/hw_model && unzip -qo en_ko.argosmodel && cd - >/dev/null
cp /tmp/hw_model/en_ko/model/model.bin /tmp/hw_model/en_ko/model/shared_vocabulary.txt /tmp/hw_model/en_ko/sentencepiece.model model/en_ko/
cp /tmp/hw_model/en_ko/README.md model/en_ko/MODEL_README.md
