# Webshop / Game / Wisdom Tree Builders

The specialized templates. Each scaffolds the repo structure and design
language; the domain logic is yours to grow.

## Webshop - `operation="webshop"`

E-commerce foundation: storefront layout, product catalog placeholder,
cart scaffold.

- **Usage**: `scaffold_ops(operation="webshop", name="my-shop", config={...})`
- **Output**: storefront repo with product/cart structure
- **Limits**: `config` required. No payment, no inventory, no auth
  generated - the catalog and cart are structure, not commerce.

## Browser Game - `operation="game"`

Interactive browser-based game using Canvas API or WebGL.

- **Usage**: `scaffold_ops(operation="game", name="my-game", config={...})`
- **Output**: game scaffold with canvas/loop skeleton
- **Limits**: `config` required. The game logic is yours - the scaffold
  provides the loop, not the fun.

## Wisdom Tree - `operation="wisdom_tree"`

Interactive knowledge graph visualization for exploring complex topics.

- **Usage**: `scaffold_ops(operation="wisdom_tree", name="my-tree", config={...})`
- **Output**: knowledge tree interface scaffold
- **Limits**: `config` required. Data sources and graph layout are yours.

## Shared notes

All three follow the same contract: structure + design language +
placeholder domain code, and an honest `config` requirement. If your
target needs more than structure, the fullstack builder is the better
starting point - it ships working backend endpoints with SQLite.
