"""
Tool for creating premium landing pages for MCP projects.
"""

import logging
from pathlib import Path


class LandingPageBuilder:
    """Builder for premium landing pages."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def create_landing_page(
        self,
        project_name: str,
        hero_title: str = "The Next Big Thing",
        hero_subtitle: str = "Revolutionizing the way you do things.",
        features: list[str] | None = None,
        github_url: str = "https://github.com",
        target_path: str = ".",
        author_name: str = "Developer",
        author_bio: str = "Expert software engineer.",
        donate_link: str = "#",
        heroimage: bool = False,
        reacttailwind: bool = False,
        feature_images: list[str] | None = None,
    ) -> str:
        """Creates a premium, multi-page landing page site."""

        # Default features
        if not features:
            features = [
                "Blazing Fast: Engineered for maximum velocity.",
                "Secure by Design: Fort Knox level security.",
                "Open Source: Transparency is key.",
            ]

        if reacttailwind:
            return await self._create_react_tailwind_app(
                project_name,
                hero_title,
                hero_subtitle,
                features,
                github_url,
                target_path,
                author_name,
                author_bio,
                donate_link,
                heroimage,
            )
        else:
            return await self._create_static_html_app(
                project_name,
                hero_title,
                hero_subtitle,
                features,
                github_url,
                target_path,
                author_name,
                author_bio,
                donate_link,
                heroimage,
            )

    async def _create_static_html_app(
        self,
        project_name,
        hero_title,
        hero_subtitle,
        features,
        github_url,
        target_path,
        author_name,
        author_bio,
        donate_link,
        heroimage,
    ) -> str:
        """Creates a static HTML landing page."""
        output_dir = Path(target_path) / project_name.lower().replace(" ", "-") / "www"
        output_dir.mkdir(parents=True, exist_ok=True)

        css_content = self._get_css_content()
        js_content = self._get_js_content()

        (output_dir / "styles.css").write_text(css_content, encoding="utf-8")
        (output_dir / "script.js").write_text(js_content, encoding="utf-8")

        # Generate pages
        pages = {
            "index.html": self._generate_index(
                project_name,
                hero_title,
                hero_subtitle,
                features,
                github_url,
                author_name,
                heroimage,
            ),
            "bio.html": f"<h1>About {author_name}</h1><p>{author_bio}</p>",
            "download.html": "<h1>Download</h1>",
            "donate.html": "<h1>Donate</h1>",
            "how_it_works.html": "<h1>How it Works</h1>",
        }

        for name, content in pages.items():
            full_html = self._wrap_html(project_name, name, content)
            (output_dir / name).write_text(full_html, encoding="utf-8")

        return str(output_dir)

    async def _create_react_tailwind_app(
        self,
        project_name,
        hero_title,
        hero_subtitle,
        features,
        github_url,
        target_path,
        author_name,
        author_bio,
        donate_link,
        heroimage,
    ) -> str:
        """Creates a React application with Tailwind CSS and animations."""
        output_dir = Path(target_path) / project_name.lower().replace(" ", "-")
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create React app structure
        src_dir = output_dir / "src"
        public_dir = output_dir / "public"
        src_dir.mkdir(exist_ok=True)
        public_dir.mkdir(exist_ok=True)

        # Generate package.json
        package_json = self._generate_package_json(project_name)
        (output_dir / "package.json").write_text(package_json, encoding="utf-8")

        # Generate tailwind.config.js
        tailwind_config = self._generate_tailwind_config()
        (output_dir / "tailwind.config.js").write_text(tailwind_config, encoding="utf-8")

        # Generate postcss.config.js
        postcss_config = self._generate_postcss_config()
        (output_dir / "postcss.config.js").write_text(postcss_config, encoding="utf-8")

        # Generate public/index.html
        index_html = self._generate_react_index_html(project_name)
        (public_dir / "index.html").write_text(index_html, encoding="utf-8")

        # Generate src/index.js
        index_js = self._generate_react_index_js()
        (src_dir / "index.js").write_text(index_js, encoding="utf-8")

        # Generate src/App.js
        app_js = self._generate_react_app(
            project_name,
            hero_title,
            hero_subtitle,
            features,
            github_url,
            author_name,
            heroimage,
        )
        (src_dir / "App.js").write_text(app_js, encoding="utf-8")

        # Generate src/index.css
        index_css = self._generate_react_css()
        (src_dir / "index.css").write_text(index_css, encoding="utf-8")

        # Generate README.md
        readme = self._generate_react_readme(project_name)
        (output_dir / "README.md").write_text(readme, encoding="utf-8")

        return str(output_dir)

    def _get_css_content(self) -> str:
        """Generate beautiful CSS for the landing page."""
        return """
        :root {
            --primary: #00f3ff;
            --secondary: #ff6b6b;
            --dark-bg: #050505;
            --text-light: #ffffff;
            --text-muted: #cccccc;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            background: var(--dark-bg);
            color: var(--text-light);
            font-family: 'Outfit', sans-serif;
            line-height: 1.6;
            min-height: 100vh;
        }

        .hero {
            min-height: 80vh;
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
            overflow: hidden;
        }

        .hero::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(135deg, rgba(0, 243, 255, 0.1) 0%, rgba(255, 107, 107, 0.1) 100%);
            z-index: -1;
        }

        .hero-content {
            text-align: center;
            max-width: 800px;
            padding: 2rem;
            z-index: 1;
        }

        .hero-title {
            font-size: clamp(2.5rem, 5vw, 4rem);
            font-weight: 700;
            margin-bottom: 1rem;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            line-height: 1.2;
        }

        .hero-subtitle {
            font-size: clamp(1.2rem, 2vw, 1.5rem);
            color: var(--text-muted);
            margin-bottom: 2rem;
            max-width: 600px;
            margin-left: auto;
            margin-right: auto;
        }

        .hero-text-only .hero-decoration {
            margin-top: 2rem;
        }

        .text-accent {
            font-size: 3rem;
            opacity: 0.8;
        }

        .hero-image {
            margin-top: 3rem;
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
        }

        .hero-image img {
            width: 100%;
            max-width: 600px;
            height: auto;
            display: block;
        }

        .features {
            padding: 4rem 2rem;
            max-width: 1200px;
            margin: 0 auto;
        }

        .features h2 {
            text-align: center;
            font-size: 2.5rem;
            margin-bottom: 3rem;
            color: var(--primary);
        }

        .feature-list {
            list-style: none;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 2rem;
        }

        .feature-item {
            background: rgba(255, 255, 255, 0.05);
            padding: 2rem;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
        }

        .cta {
            padding: 4rem 2rem;
            text-align: center;
        }

        .cta-button {
            display: inline-block;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: var(--dark-bg);
            padding: 1rem 2rem;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 600;
            margin: 0 1rem 1rem 0;
            transition: transform 0.2s ease;
        }

        .cta-button:hover {
            transform: translateY(-2px);
        }

        .cta-link {
            color: var(--primary);
            text-decoration: none;
            margin-left: 2rem;
        }

        @media (max-width: 768px) {
            .hero {
                min-height: 60vh;
                padding: 2rem 1rem;
            }

            .hero-title {
                font-size: 2.5rem;
            }

            .feature-list {
                grid-template-columns: 1fr;
            }
        }
        """

    def _get_js_content(self) -> str:
        return "console.log('Landing page initialized');"

    def _generate_index(self, project_name, title, subtitle, features, github, author, heroimage):
        """Generate the main index page with optional hero image."""
        if heroimage:
            # Include hero image
            hero_section = f"""
            <section class="hero">
                <div class="hero-content">
                    <h1 class="hero-title">{title}</h1>
                    <p class="hero-subtitle">{subtitle}</p>
                    <div class="hero-image">
                        <img src="https://images.unsplash.com/photo-1555949963-aa79dcee981c?w=800&h=400&fit=crop&crop=center" alt="Hero Image" />
                    </div>
                </div>
            </section>
            """
        else:
            # Beautiful hero text only
            hero_section = f"""
            <section class="hero hero-text-only">
                <div class="hero-content">
                    <h1 class="hero-title">{title}</h1>
                    <p class="hero-subtitle">{subtitle}</p>
                    <div class="hero-decoration">
                        <div class="text-accent">Magic</div>
                    </div>
                </div>
            </section>
            """

        # Generate features section
        features_html = ""
        if features:
            features_html = '<section class="features"><h2>Features</h2><ul class="feature-list">'
            for feature in features:
                features_html += f'<li class="feature-item">{feature}</li>'
            features_html += "</ul></section>"

        # Generate main content
        main_content = f"""
        {hero_section}
        {features_html}
        <section class="cta">
            <a href="{github}" class="cta-button" target="_blank">View on GitHub</a>
            <a href="bio.html" class="cta-link">About {author}</a>
        </section>
        """

        return main_content

    def _wrap_html(self, project_name, page_name, content):
        return f"<!DOCTYPE html><html><head><title>{project_name}</title></head><body>{content}</body></html>"

    def _generate_package_json(self, project_name: str) -> str:
        """Generate package.json for React app."""
        return f"""{{
  "name": "{project_name.lower().replace(" ", "-")}",
  "version": "0.1.0",
  "private": true,
  "dependencies": {{
    "@heroicons/react": "^2.0.18",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-scripts": "5.0.1",
    "web-vitals": "^2.1.4"
  }},
  "scripts": {{
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test",
    "eject": "react-scripts eject"
  }},
  "eslintConfig": {{
    "extends": [
      "react-app",
      "react-app/jest"
    ]
  }},
  "browserslist": {{
    "production": [
      ">0.2%",
      "not dead",
      "not op_mini all"
    ],
    "development": [
      "last 1 chrome version",
      "last 1 firefox version",
      "last 1 safari version"
    ]
  }},
  "devDependencies": {{
    "tailwindcss": "^3.3.3",
    "autoprefixer": "^10.4.14",
    "postcss": "^8.4.24"
  }}
}}
"""

    def _generate_tailwind_config(self) -> str:
        """Generate Tailwind CSS configuration."""
        return """/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f0f9ff',
          500: '#00f3ff',
          600: '#00d4ff',
          900: '#001a1d',
        },
        secondary: {
          500: '#ff6b6b',
          600: '#ff5555',
        },
        dark: {
          50: '#f8f9fa',
          900: '#050505',
          800: '#1a1a1a',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      animation: {
        'fade-in': 'fadeIn 0.6s ease-in-out',
        'slide-up': 'slideUp 0.6s ease-out',
        'bounce-subtle': 'bounceSubtle 2s infinite',
        'float': 'float 3s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(30px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        bounceSubtle: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-5px)' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-10px)' },
        },
      },
    },
  },
  plugins: [],
}
"""

    def _generate_postcss_config(self) -> str:
        """Generate PostCSS configuration."""
        return """module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
"""

    def _generate_react_index_html(self, project_name: str) -> str:
        """Generate React index.html."""
        return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <link rel="icon" href="%PUBLIC_URL%/favicon.ico" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="theme-color" content="#00f3ff" />
    <meta name="description" content="Beautiful landing page for {project_name}" />
    <link rel="apple-touch-icon" href="%PUBLIC_URL%/logo192.png" />
    <link rel="manifest" href="%PUBLIC_URL%/manifest.json" />
    <title>{project_name}</title>
  </head>
  <body>
    <noscript>You need to enable JavaScript to run this app.</noscript>
    <div id="root"></div>
  </body>
</html>
"""

    def _generate_react_index_js(self) -> str:
        """Generate React index.js."""
        return """import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
"""

    def _generate_react_app(
        self,
        project_name: str,
        hero_title: str,
        hero_subtitle: str,
        features: list[str],
        github_url: str,
        author_name: str,
        heroimage: bool,
    ) -> str:
        """Generate main React App component with Tailwind and animations."""
        features_js = ",\n    ".join([f'"{feature}"' for feature in features])

        # Generate React app code
        hero_image_section = ""
        if heroimage:
            hero_image_section = """            <div className="mb-12 animate-float">
              <img
                src="https://images.unsplash.com/photo-1555949963-aa79dcee981c?w=600&h=300&fit=crop&crop=center"
                alt="Hero"
                className="mx-auto rounded-2xl shadow-2xl max-w-md"
              />
            </div>"""
        else:
            hero_image_section = """            <div className="mb-12 animate-bounce-subtle">
              <div className="text-6xl opacity-80">Magic</div>
            </div>"""

        template = """import React, { useState, useEffect } from 'react';
import { StarIcon, BoltIcon, ShieldCheckIcon } from '@heroicons/react/24/solid';

function App() {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    setIsVisible(true);
  }, []);

  const features = [
    __FEATURES_JS__
  ];

  return (
    <div className="min-h-screen bg-dark-900 text-white">
      <section className="relative min-h-screen flex items-center justify-center overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-primary-500/10 via-secondary-500/5 to-transparent"></div>

        <div className={`relative z-10 text-center max-w-4xl mx-auto px-6 py-20 transition-opacity duration-1000 ${isVisible ? 'opacity-100' : 'opacity-0'}`}>
          <h1 className="text-5xl md:text-7xl font-bold mb-6 bg-gradient-to-r from-primary-500 to-secondary-500 bg-clip-text text-transparent animate-fade-in">
            __HERO_TITLE__
          </h1>

          <p className="text-xl md:text-2xl text-gray-300 mb-12 max-w-3xl mx-auto animate-slide-up">
            __HERO_SUBTITLE__
          </p>

          __HERO_IMAGE_SECTION__

          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <a
              href="__GITHUB_URL__"
              className="bg-gradient-to-r from-primary-500 to-primary-600 hover:from-primary-600 hover:to-primary-700 text-dark-900 font-semibold py-3 px-8 rounded-lg transition-all duration-300 transform hover:scale-105 hover:shadow-lg"
            >
              View on GitHub
            </a>
            <a
              href="#features"
              className="border border-primary-500 text-primary-500 hover:bg-primary-500 hover:text-dark-900 font-semibold py-3 px-8 rounded-lg transition-all duration-300"
            >
              Learn More
            </a>
          </div>
        </div>
      </section>

      <section id="features" className="py-20 px-6">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-4xl md:text-5xl font-bold text-center mb-16 bg-gradient-to-r from-primary-500 to-secondary-500 bg-clip-text text-transparent">
            Features
          </h2>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((feature, index) => (
              <div
                key={index}
                className="group bg-dark-800/50 backdrop-blur-sm border border-white/10 rounded-xl p-6 hover:bg-dark-800/70 hover:border-primary-500/50 transition-all duration-300 transform hover:scale-105 hover:shadow-xl"
              >
                <div className="mb-4">
                  {index === 0 && <BoltIcon className="w-8 h-8 text-primary-500 group-hover:animate-pulse" />}
                  {index === 1 && <ShieldCheckIcon className="w-8 h-8 text-secondary-500 group-hover:animate-pulse" />}
                  {index === 2 && <StarIcon className="w-8 h-8 text-primary-500 group-hover:animate-pulse" />}
                </div>
                <p className="text-gray-300 group-hover:text-white transition-colors duration-300">
                  {feature}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="py-20 px-6 bg-gradient-to-r from-primary-500/10 to-secondary-500/10">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl md:text-4xl font-bold mb-6">
            Ready to Get Started?
          </h2>
          <p className="text-xl text-gray-300 mb-8">
            Join thousands of developers using __PROJECT_NAME__
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <a
              href="__GITHUB_URL__"
              className="bg-gradient-to-r from-primary-500 to-primary-600 hover:from-primary-600 hover:to-primary-700 text-dark-900 font-semibold py-3 px-8 rounded-lg transition-all duration-300 transform hover:scale-105 hover:shadow-lg"
            >
              Get Started
            </a>
            <a
              href="#about"
              className="border border-primary-500 text-primary-500 hover:bg-primary-500 hover:text-dark-900 font-semibold py-3 px-8 rounded-lg transition-all duration-300"
            >
              About __AUTHOR_NAME__
            </a>
          </div>
        </div>
      </section>

      <footer id="about" className="py-12 px-6 border-t border-white/10">
        <div className="max-w-4xl mx-auto text-center">
          <p className="text-gray-400">
            Built with made with love by  by __AUTHOR_NAME__
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;
"""
        app_code = template.replace("__FEATURES_JS__", features_js)
        app_code = app_code.replace("__HERO_TITLE__", hero_title)
        app_code = app_code.replace("__HERO_SUBTITLE__", hero_subtitle)
        app_code = app_code.replace("__HERO_IMAGE_SECTION__", hero_image_section)
        app_code = app_code.replace("__GITHUB_URL__", github_url)
        app_code = app_code.replace("__PROJECT_NAME__", project_name)
        app_code = app_code.replace("__AUTHOR_NAME__", author_name)

        return app_code

    def _generate_react_css(self) -> str:
        """Generate React CSS with Tailwind imports."""
        return """@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  html {
    scroll-behavior: smooth;
  }
}

@layer components {
  .btn-primary {
    @apply bg-gradient-to-r from-primary-500 to-primary-600 hover:from-primary-600 hover:to-primary-700 text-dark-900 font-semibold py-3 px-8 rounded-lg transition-all duration-300 transform hover:scale-105 hover:shadow-lg;
  }

  .card-hover {
    @apply bg-dark-800/50 backdrop-blur-sm border border-white/10 rounded-xl p-6 hover:bg-dark-800/70 hover:border-primary-500/50 transition-all duration-300 transform hover:scale-105 hover:shadow-xl;
  }
}
"""

    def _generate_react_readme(self, project_name: str) -> str:
        """Generate README for React app."""
        return f"""# {project_name}

A beautiful, modern React landing page built with Tailwind CSS and stunning animations.

## Process Features

- Magic Beautiful animations and hover effects
- Design Modern Tailwind CSS styling
- Mobile Fully responsive design
- Bolt Fast and performant
- Mask Interactive card animations

##  Getting Started

### Prerequisites

Make sure you have Node.js installed on your system.

### Installation

1. Install dependencies:
```bash
npm install
```

2. Start the development server:
```bash
npm start
```

3. Open [http://localhost:3000](http://localhost:3000) to view it in your browser.

### Build for Production

```bash
npm run build
```

This builds the app for production to the `build` folder.

## Design Customization

### Colors
The app uses a custom color palette defined in `tailwind.config.js`:
- Primary: Cyan (#00f3ff)
- Secondary: Red (#ff6b6b)
- Dark theme with gradients

### Animations
- Fade-in animations on load
- Hover effects on cards and buttons
- Floating animations for decorative elements
- Scale transforms on interactive elements

### Components
- Hero section with optional image
- Feature cards with hover animations
- Call-to-action buttons
- Responsive navigation

## Mobile Responsive Design

The app is fully responsive and works beautifully on:
- Mobile Mobile devices
- Computer Tablets
-  Desktop computers

## Mask Animations

- **Fade In**: Elements fade in smoothly on page load
- **Slide Up**: Content slides up into view
- **Hover Effects**: Cards lift and glow on hover
- **Button Animations**: Buttons scale and change colors
- **Floating Elements**: Decorative elements float gently

##  Tech Stack

- **React** - Frontend framework
- **Tailwind CSS** - Utility-first CSS framework
- **Heroicons** - Beautiful hand-crafted SVG icons
- **PostCSS** - CSS processing
- **Autoprefixer** - CSS vendor prefixing

##  License

This project is open source and available under the [MIT License](LICENSE).
"""
