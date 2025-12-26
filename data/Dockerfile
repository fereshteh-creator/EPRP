FROM node:20-alpine

RUN apk add --no-cache python3 make g++ git

# Install Dolos
RUN npm install -g @dodona/dolos


# =========================
# LUA FIX (install a TS-0.25 compatible lua grammar INSIDE dolos)
# =========================
RUN npm install --legacy-peer-deps --prefix /usr/local/lib/node_modules/@dodona/dolos \
    @tree-sitter-grammars/tree-sitter-lua

# Alias it to the exact name Dolos imports: "tree-sitter-lua"
RUN mkdir -p /usr/local/lib/node_modules/@dodona/dolos/node_modules/tree-sitter-lua && \
    printf '%s\n' \
'{' \
'  "name": "tree-sitter-lua",' \
'  "version": "0.0.0",' \
'  "private": true,' \
'  "type": "module",' \
'  "main": "./index.js",' \
'  "exports": "./index.js"' \
'}' \
    > /usr/local/lib/node_modules/@dodona/dolos/node_modules/tree-sitter-lua/package.json && \
    printf '%s\n' \
'import pkg from "@tree-sitter-grammars/tree-sitter-lua";' \
'export default pkg;' \
'export * from "@tree-sitter-grammars/tree-sitter-lua";' \
    > /usr/local/lib/node_modules/@dodona/dolos/node_modules/tree-sitter-lua/index.js


# Install other grammars globally (optional)
# IMPORTANT: remove tree-sitter-lua here (it was incompatible)
RUN npm install -g \
    tree-sitter-c \
    tree-sitter-go \
    tree-sitter-haskell \
    tree-sitter-java \
    tree-sitter-javascript \
    tree-sitter-julia \
    tree-sitter-python \
    tree-sitter-ruby \
    tree-sitter-rust \
    tree-sitter-scala


# =========================
# PERL FIX (already working)
# =========================
RUN npm install --legacy-peer-deps --prefix /usr/local/lib/node_modules/@dodona/dolos \
    @ganezdragon/tree-sitter-perl

RUN mkdir -p /usr/local/lib/node_modules/@dodona/dolos/node_modules/tree-sitter-perl && \
    printf '%s\n' \
'{' \
'  "name": "tree-sitter-perl",' \
'  "version": "0.0.0",' \
'  "private": true,' \
'  "type": "module",' \
'  "main": "./index.js",' \
'  "exports": "./index.js"' \
'}' \
    > /usr/local/lib/node_modules/@dodona/dolos/node_modules/tree-sitter-perl/package.json && \
    printf '%s\n' \
'import pkg from "@ganezdragon/tree-sitter-perl";' \
'export default pkg;' \
'export * from "@ganezdragon/tree-sitter-perl";' \
    > /usr/local/lib/node_modules/@dodona/dolos/node_modules/tree-sitter-perl/index.js


WORKDIR /workspace
ENTRYPOINT ["dolos"]
