# Linting  

## Setup  
1. Ensure you are in the root directory: `homelab`  
2. Run: `make env`  
3. Run: `source .venv/bin/activate`  
  
The last command will put you into a virtual env with this projects' specific dependencies.  
To exit, do not type `exit`. Type `deactivate`.  
  
## Tools  
  
### Linting  
```  
flake8  
mypy  
Vulture - dead code  
pydocstyle - Docstring styling  
bandit - find common security issues  
```  
  
### Formatting  
```  
black  
isort  
```  
  
### TBD  
  
```  
detect-secrets-hook - determine if any potential secrets/password leaking is happening  
```  
  
## Local - Branch Only  
1. Run: `make check-commit-modified-files`  
  
This will produce a list of items that need attention in your current branch.  
  
## Local - Entire Project  

1. Run: `make check-project-all`  
  
## Hooks  
  
### Pre-commit  
  
### Post Commit