# 🔗 Contributing

Contributions are welcome! Please follow these steps to get started:

## 🛠 How to Contribute

1. Fork the repository
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/llm-parse
   cd llm-parse
   ```
3. Set up the development environment:
   ```bash
   direnv allow  # or manually activate conda environment
   make setup
   ```
4. Run checks and build docs:
   ```bash
   make check
   make docs
   ```
5. Create a new branch, make changes, and open a PR

## 📏 Code Style

* Follow formatting rules via `black`, `ruff`, and `isort`
* Use `pre-commit` to run checks automatically

## 🧪 Testing

* Currently NA — feel free to propose tests or integrate a framework

## 📘 Docs

* Docs are in `docs/` using Sphinx
* Update `.rst` files if needed and run:
  ```bash
  make docs
  ```

## 📄 Issues

* Use GitHub Issues to report bugs or propose features
* Use Discussions if enabled for open-ended questions or ideas

---

Thank you for contributing! 🙏
