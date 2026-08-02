# PowerShell Best Practices for Windows Development

## 🎯 "Argh-Coding" Prevention Guide

This guide prevents the most common PowerShell syntax issues that LLMs suggest in Windows environments, ensuring smooth development workflows in Windsurf.

## 🚨 Critical Issues to Avoid

### **1. Linux Commands in PowerShell (REAL PROBLEM!)**
```powershell
# ❌ WRONG - These don't exist in PowerShell
ls -la
grep -r
chmod +x
sudo apt-get
cat file.conf
tail -f
head -n
ssh -c "command"
bash -c "command"
export VAR=value
echo "message"
find . -name "*.py"
du -sh
ps aux
kill -9
top -n
free -h
df -h

# ⚠️ CONDITIONAL - These work if installed in PATH
wget https://example.com  # Works if wget is installed
curl https://api.example.com  # Works if curl is installed

# ✅ CORRECT - Use PowerShell equivalents (more reliable)
Get-ChildItem -Force | Format-Table
Select-String -Pattern "pattern"
Set-ItemProperty -Path -Name ReadOnly -Value $false
Install-Package -Name "package"
Get-Content -Path "file.conf"
Get-Content -Path "file.txt" -Tail 10
Get-Content -Path "file.txt" -TotalCount 10
Invoke-WebRequest -Uri "https://example.com"  # Native PowerShell
Invoke-WebRequest -Uri "https://api.example.com"  # Native PowerShell
Invoke-Expression "command"
pwsh -Command "command"
Set-Item -Path "VAR" -Value "value"
Write-Host "message"
Get-ChildItem -Recurse -Filter "*.py"
Get-ChildItem -Recurse -File | Measure-Object Length | Sort-Object Length -Descending
Get-Process | Format-Table Name, CPU, Id, StartTime, Memory
Stop-Process -Id 1234
Get-Process | Sort-Object CPU -Descending | Select-Object -First 10
Get-Process | Measure-Object WorkingSet | Sort-Object WorkingSet -Descending | Select-Object -First 10
Get-Volume | Format-Table Name, Size, Used, Free
```

### **2. Parameter Redundancy (COMMON LLM MISTAKE!)**
```powershell
# ❌ WRONG - Redundant parameters
Get-ChildItem -Path "C:\folder"
Set-Content -Path "file.txt" "content"
Test-Path -Path "file.txt"
Copy-Item -Source "source" -Destination "dest"
Move-Item -Source "source" -Destination "dest"
Remove-Item -Path "folder" -Recurse

# ✅ CORRECT - Native PowerShell syntax
Get-ChildItem "C:\folder"
Set-Content "file.txt" "content"
Test-Path "file.txt"
Copy-Item "source" "dest"
Move-Item "source" "dest"
Remove-Item "folder" -Recurse
```

### **3. Command-Line Patterns (INEFFICIENT!)**
```powershell
# WRONG - Linux-style patterns (work but not native)
mkdir -p folder1 folder2 folder3
rm -rf folder1 folder2 folder3
cp -r source dest
mv old_name new_name
touch file.txt
chmod +x script.ps1
find . -name "*.py" -exec grep "pattern" {} \;
xargs grep "pattern" *.txt
awk '{print $1}' file.txt
sed 's/old/new/g' file.txt

# CORRECT - Native PowerShell cmdlets (BEST PRACTICE!)
New-Item -Type Directory -Force folder1, folder2, folder3
Remove-Item -Recurse -Force folder1, folder2, folder3
Copy-Item -Recurse -Force source dest
Move-Item -Force old_name new_name
New-Item -Type File file.txt
Set-ItemProperty -Path script.ps1 -Name ReadOnly -Value $false
Get-ChildItem -Recurse -Filter "*.py" | ForEach-Object { Select-String "pattern" }
Get-ChildItem -Filter "*.txt" | ForEach-Object { Select-String "pattern" }
ForEach-Object { $_.Replace("old", "new") } file.txt
Compress-Archive -Path "archive.zip" -Destination "source"
```

### **4. Windows-Specific Gotchas (MICROSOFT ALIASING ISSUES!)**
```powershell
# ❌ WRONG - Microsoft aliases that don't work reliably
python script.py  # May not work due to aliasing issues
python3 script.py  # May not work due to aliasing issues
where python  # May not work due to aliasing issues

# ⚠️ CONDITIONAL - These work if installed in PATH
pip install package  # Works if pip is installed
pip3 install package  # Works if pip3 is installed

# ✅ CORRECT - Use explicit executable paths
python.exe script.py  # Always works
python.exe -m pip install package  # Always works
python.exe -m pip install --upgrade package  # Always works
Get-Command python  # Always works

# Alternative: Use full Python path
C:\Python39\python.exe script.py  # Always works
C:\Python39\python.exe -m pip install package  # Always works
```

### **5. Build Script Patterns (COMMON BUILD ISSUES!)**
```powershell
# ❌ WRONG - Empty directory issue
New-Item -Type Directory -Force builddir; cd builddir; runbuild  # Empty directory → cd fails!

# ❌ WRONG - Linux-style command chaining
cd builddir && runbuild  # Fails due to && syntax

# ✅ CORRECT - Native PowerShell build patterns
# Option 1: Create directory with content (if needed)
New-Item -Type Directory -Force builddir; Set-Content builddir\README.md "Build directory"; cd builddir; runbuild

# Option 2: Use existing directory (if it exists)
if (Test-Path builddir) { cd builddir; runbuild } else { Write-Host "Build directory not found" -ForegroundColor Red }

# Option 3: Create directory and copy build files (if needed)
New-Item -Type Directory -Force builddir; Copy-Item -Recurse -Force "source\*" "builddir\"; cd builddir; runbuild

# Option 4: Use absolute paths (most reliable)
cd "D:\Projects\myproject\builddir"; runbuild  # Always works if path exists
```

### **5. Command-Line Patterns (INEFFICIENT!)**
```powershell
# WRONG - Linux-style patterns (work but not native)
mkdir -p folder1 folder2 folder3
rm -rf folder1 folder2 folder3
cp -r source dest
mv old_name new_name
touch file.txt
chmod +x script.ps1
find . -name "*.py" -exec grep "pattern" {} \;
xargs grep "pattern" *.txt
awk '{print $1}' file.txt
sed 's/old/new/g' file.txt

# CORRECT - Native PowerShell cmdlets (BEST PRACTICE!)
New-Item -Type Directory -Force folder1, folder2, folder3
Remove-Item -Recurse -Force folder1, folder2, folder3
Copy-Item -Recurse -Force source dest
Move-Item -Force old_name new_name
New-Item -Type File file.txt
Set-ItemProperty -Path script.ps1 -Name ReadOnly -Value $false
Get-ChildItem -Recurse -Filter "*.py" | ForEach-Object { Select-String "pattern" }
Get-ChildItem -Filter "*.txt" | ForEach-Object { Select-String "pattern" }
ForEach-Object { $_.Replace("old", "new") } file.txt
Compress-Archive -Path "archive.zip" -Destination "source"
```

## Best Practices

### **Directory Operations**
```powershell
# Create multiple directories at once
New-Item -Type Directory -Force folder1, folder2, folder3

# Create directory with permissions
New-Item -Type Directory -Path "folder" -Force

# Create nested directory structure
New-Item -Type Directory -Path "parent\child\grandchild" -Force
```

### **File Operations**
```powershell
# Create empty file
New-Item -Type File -Path "file.txt"

# Create file with content
Set-Content "file.txt" "content"

# Copy files with progress
Copy-Item -Recurse -Force "source" -Destination "dest"

# Move files
Move-Item -Force "old_name" "new_name"

# Remove files and directories
Remove-Item -Recurse -Force "folder"
Remove-Item "file.txt"
```

### **Advanced Operations**
```powershell
# Search files with specific patterns
Get-ChildItem -Recurse -Filter "*.py" | Where-Object { $_.Name -like "*test*" }

# Process files in pipeline
Get-Content "file.txt" | Select-String "error" | ForEach-Object { Write-Host "Found error: $_" -ForegroundColor Red }

# Sort files by size
Get-ChildItem -Recurse -File | Measure-Object Length | Sort-Object Length -Descending | Select-Object -First 10
```

## Enhanced Response Patterns

### **Validation Response Example:**
```python
{
    "success": True,
    "operation": "validate_powershell_syntax",
    "result": {
        "total_syntax_issues": 15,
        "files_with_issues": 4,
        "syntax_issues": [
            {
                "issue_type": "linux_command_in_powershell",
                "problematic_match": "mkdir -p folder1 folder2 folder3",
                "suggested_fix": "New-Item -Type Directory -Force folder1, folder2, folder3",
            },
            {
                "issue_type": "cmdlet_usage_pattern",
                "problematic_match": "cp -r src dest",
                "suggested_fix": "Copy-Item -Recurse -Force src dest",
            },
        ],
    },
    "summary": "Found 4 PowerShell files with 15 syntax issues (8 Linux commands, 4 parameter redundancy, 3 cmdlet patterns)",
    "recommendations": [
        "Use native PowerShell cmdlets for better performance",
        "Avoid Linux command patterns in PowerShell scripts",
        "Use proper PowerShell parameter syntax",
        "Use native PowerShell cmdlet patterns for folder scaffolding",
    ],
    "next_steps": [
        "Test fixed scripts in PowerShell",
        "Learn native PowerShell cmdlets",
        "Use validate_powershell_syntax() for ongoing validation",
    ],
}
```

## Quick Reference

### **Directory Operations**
| Linux Command | PowerShell Equivalent | Native? |
|---------------|---------------------|----------|
| `ls -la` | `Get-ChildItem -Force | Format-Table` | |
| `mkdir -p` | `New-Item -Type Directory -Force` | |
| `rm -rf` | `Remove-Item -Recurse -Force` | |
| `cp -r` | `Copy-Item -Recurse -Force` | |
| `mv` | `Move-Item -Force` | |

### **File Operations**
| Linux Command | PowerShell Equivalent | Native? |
|---------------|---------------------|----------|
| `cat` | `Get-Content` | |
| `touch` | `New-Item -Type File` | |
| `chmod +x` | `Set-ItemProperty -Path -Name ReadOnly -Value $false` | |
| `echo` | `Write-Host` | |

### **Advanced Operations**
| Linux Command | PowerShell Equivalent | Native? |
|---------------|---------------------|----------|
| `find` | `Get-ChildItem -Recurse` | |
| `grep` | `Select-String` | |
| `sort` | `Sort-Object` | |
| `uniq` | `Sort-Object -Unique` | |
| `tar` | `Compress-Archive` | |
| `zip` | `Compress-Archive` | |
| `head` | `Get-Content -TotalCount 10` | |
| `tail` | `Get-Content -Tail 10` | |
| `&&` | `;` (use semicolon) | |
| `|` (pipe) | `|` (use pipeline operator) | |

### **Pipeline Operations:**
```powershell
# Linux-style (works but not native)
ls -la | grep "pattern" | wc -l

# Native PowerShell (BEST PRACTICE!)
Get-ChildItem -Force | Select-String "pattern" | Measure-Object Line
```

### **Command Chaining:**
```powershell
# Linux-style (works but not native)
ls -la && grep "error" && echo "Found errors"

# Native PowerShell (BEST PRACTICE!)
Get-ChildItem -Force | Where-Object { $_.Name -like "*error*" } | ForEach-Object { Write-Host "Found error in: $($_.Name)" -ForegroundColor Red }
```

### **Real-World Examples:**

#### **Log Analysis:**
```powershell
# Linux-style (works but not native)
Get-Content "app.log" | tail -f | grep "ERROR" | wc -l

# Native PowerShell (BEST PRACTICE!)
Get-Content "app.log" | Select-String "ERROR" -Tail 10 | Measure-Object Line
```

#### **Process Monitoring:**
```powershell
# Linux-style (works but not native)
ps aux | grep "process_name" | head -n

# Native PowerShell (BEST PRACTICE!)
Get-Process | Where-Object { $_.ProcessName -like "*process_name*" } | Select-Object -First 10
```

#### **File Processing:**
```powershell
# Linux-style (works but not native)
find . -name "*.log" -exec grep "ERROR" {} \; | wc -l

# Native PowerShell (BEST PRACTICE!)
Get-ChildItem -Recurse -Filter "*.log" | ForEach-Object { Select-String "ERROR" } | Measure-Object Line
```

## Pipeline Best Practices

### **Use Pipeline Operator:**
```powershell
# Native PowerShell pipeline operator
Get-Content "file.txt" | Select-String "error" | Measure-Object Line
Get-ChildItem -Force | Where-Object { $_.Extension -eq ".ps1" } | ForEach-Object { Write-Host "PowerShell file: $($_.Name)" }
```

### **Use Semicolon for Command Chaining:**
```powershell
# Native PowerShell command chaining
Get-ChildItem -Force; Write-Host "Files listed"; Get-Process | Format-Table Name, CPU
```

### **Avoid Mixed Patterns:**
```powershell
# Mixed Linux/PowerShell (confusing!)
ls -la | grep "pattern"  # Linux command + PowerShell pipeline

# Pure PowerShell (BEST PRACTICE!)
Get-ChildItem -Force | Select-String "pattern"  # Pure PowerShell
```

## Why This Matters for Windsurf Users

### **Prevents Pipeline Failures:**
- **Linux pipelines**: `ls -la | grep "pattern"` may fail with complex patterns
- **Command chaining**: `&&` operator doesn't work in PowerShell
- **Pipe operations**: `|` operator may have different behavior

### **Improves Script Reliability:**
- **Native pipelines**: More reliable in Windows environments
- **Semicolon chaining**: Proper command execution order
- **Pipeline operator**: Consistent behavior across PowerShell versions

### **Educational Value:**
- **Teaches PowerShell pipeline syntax**
- **Shows proper command chaining methods**
- **Demonstrates native PowerShell patterns**

### **Implementation Priority:**

#### **HIGH Priority:**
1. **Add to `.windsurf/rules/` directory**
2. **Include in project-specific rulebooks**
3. **Add to global Windsurf configuration**

#### **MEDIUM Priority:**
1. **Add to team documentation**
2. **Include in onboarding materials**
3. **Add to CI/CD documentation**

#### **LOW Priority:**
1. **Add to personal reference guides**
2. **Include in training materials**
3. **Add to community guidelines**

---

**Remember**: In PowerShell, **native cmdlets and proper pipeline syntax** are always preferred over Linux command patterns for better performance, reliability, and maintainability! 
