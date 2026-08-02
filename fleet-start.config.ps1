# Per-repo fleet start config for meta_mcp
# Edit ports/backend target here - start.ps1 is fleet-standard.
@{
    Name         = 'meta_mcp'
    BackendPort  = 10718
    FrontendPort = 10719
    HealthPath   = '/health'
    WebRoot      = 'D:\Dev\repos\meta_mcp\web_sota'
    Backend = @{
        Kind          = 'uvicorn'
        UvicornTarget = 'meta_mcp.server:app'
        Env           = @{ WEB_PORT = '10718' }
    }
    Frontend = @{
        Kind           = 'vite-npm'
        PackageManager = 'npm'
        PortEnvVar     = 'VITE_PORT'
        ApiTargetEnv   = 'VITE_API_TARGET'
    }
}
