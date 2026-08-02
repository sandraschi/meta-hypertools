from pydantic import BaseModel


class FullstackAppConfig(BaseModel):
    name: str = ""
    description: str = "A modern fullstack application"
    author: str = "Developer"
    target_path: str = "./apps"
    include_ai: bool = True
    include_mcp: bool = True
    include_mcp_server: bool = True
    include_pwa: bool = True
    include_monitoring: bool = True


class LandingPageConfig(BaseModel):
    project_name: str = ""
    hero_title: str = "The Next Big Thing"
    hero_subtitle: str = "Revolutionizing the way you do things"
    github_url: str = "https://github.com"
    target_path: str = "."
    author_name: str = "Developer"
    author_bio: str = "I build amazing things"
    show_locally: bool = False
