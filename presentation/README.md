# Nautilus Playground Presentation

This is a presentation for the Nautilus Playground project created using [Slidev](https://sli.dev/).

## Getting Started

### Prerequisites

- [Node.js](https://nodejs.org/) (v18 or higher)
- [pnpm](https://pnpm.io/) (recommended) or npm

### Installation

1. Clone this repository
2. Navigate to the presentation directory
3. Install dependencies:

```bash
pnpm install
# or
npm install
```

### Running the Presentation

To start the presentation in development mode:

```bash
# Using the provided script
./scripts/run.sh

# Or manually
pnpm dev
# or
npm run dev
```

This will start the presentation and open it in your default browser at http://localhost:3030.

### Building for Production

To build the presentation for production:

```bash
pnpm build
# or
npm run build
```

This will generate a static version of the presentation in the `dist` directory.

### Exporting to PDF

To export the presentation to PDF:

```bash
# Using the provided script
./scripts/export.sh

# Or manually
pnpm export
# or
npm run export
```

This requires the `playwright-chromium` package, which is included in the devDependencies.

## Customization

You can customize the presentation by editing the `slides.md` file. For more information on how to use Slidev, check out the [Slidev documentation](https://sli.dev/).

## License

This presentation is licensed under the same license as the Nautilus Playground project.
