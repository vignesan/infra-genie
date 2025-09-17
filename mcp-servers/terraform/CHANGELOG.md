## Unreleased

FEATURES

* Adding tools for working with workspaces in HCP Terraform and TFE.
* Authentication for HCP Terraform & TFE and restructure the repo. See [#121](https://github.com/hashicorp/terraform-mcp-server/pull/121) See [#145](https://github.com/hashicorp/terraform-mcp-server/pull/145)
* Implement dynamic tool registration. See [#121](https://github.com/hashicorp/terraform-mcp-server/pull/121)
* Adding 2 new HCP TF/TFE tools for admins. List Terraform organizations & projects. See [#121](https://github.com/hashicorp/terraform-mcp-server/pull/121)
* Adding 4 new HCP TF/TFE tools for private registry support. See [#142](https://github.com/hashicorp/terraform-mcp-server/pull/142)
* Adding 4 new HCP TF/TFE tools for creating Terraform runs. See [#159](https://github.com/hashicorp/terraform-mcp-server/pull/159)

IMPROVEMENTS

* Changes to tool names to be more consistent. See [#121](https://github.com/hashicorp/terraform-mcp-server/pull/121)
* Implement pagination utility. See [#121](https://github.com/hashicorp/terraform-mcp-server/pull/121)
* Updating `mark3labs/mcp-go` and `hashicorp/tfe-go` versions. See [#121](https://github.com/hashicorp/terraform-mcp-server/pull/121)
* Implemented rate limiting with the MCP server. See [#155](https://github.com/hashicorp/terraform-mcp-server/pull/155)

FIXES

* Fixing paths using in-built library instead of string manipulation. See [#143](https://github.com/hashicorp/terraform-mcp-server/pull/143)
* Explicitly setting destructive annotation to false. See [#143](https://github.com/hashicorp/terraform-mcp-server/pull/143)

SECURITY

* Rename TFE_SKIP_TLS_VERIFY environment variable and fix GitHub Action security issue. See [#164](https://github.com/hashicorp/terraform-mcp-server/pull/164)
* Update go version from 1.24.6 to 1.24.7

## 0.2.3 (Aug 13, 2025)

FEATURES

* User agent to identify calls made to the Terraform registry. See [133](https://github.com/hashicorp/terraform-mcp-server/pull/133)
* Adding Issue templates, GitHub workflows and golang version. See [134](https://github.com/hashicorp/terraform-mcp-server/pull/134)

FIXES

* run-http command in makefile is fixed. See [132](https://github.com/hashicorp/terraform-mcp-server/pull/132)

## 0.2.2 (Aug 5, 2025)

FEATURES

* 2 New tools, get latest provider and module versions. See [#122](https://github.com/hashicorp/terraform-mcp-server/pull/122)

IMPROVEMENTS

* Restructure the codebase, changes too tool names from camelCase to snake_case. See [#118](https://github.com/hashicorp/terraform-mcp-server/pull/118)
* Change tool names to be more consistent. See [#123](https://github.com/hashicorp/terraform-mcp-server/pull/123)

FIXES

* Enhanced provider documentation tool. See [#120](https://github.com/hashicorp/terraform-mcp-server/pull/120)
* StreamableHttp endpoint customization, thanks to @sachinmalanki. See [#116](https://github.com/hashicorp/terraform-mcp-server/pull/116)

## 0.2.1 (July 11, 2025)

SECURITY

* Added support for CORS (strict, development, disabled), default mode is strict. See [#108](https://github.com/hashicorp/terraform-mcp-server/pull/108)
* Added support for CORS allowed origins, default is empty. See [#108](https://github.com/hashicorp/terraform-mcp-server/pull/108)
* Added support for stateless streamable HTTP mode, see [#108](https://github.com/hashicorp/terraform-mcp-server/pull/108)

IMPROVEMENTS

* Improved the HTTP retry to the registry. See [#109](https://github.com/hashicorp/terraform-mcp-server/pull/109)

## 0.2.0 (July 3, 2025)

SECURITY

* Updated Docker base image to `scratch` for smaller, more secure production images.
* Integrated security scanning (CodeQL, security scanner) and improved CI workflows for better code quality and vulnerability detection.
* Update golang stdlib version to 1.24.4

FEATURES

* Added support for publishing Docker images to Amazon ECR
* Added support for searching and getting documentation for policies from the Terraform Registry
* Enhanced toolset for resolving provider documentation, fetching provider docs, searching modules, and retrieving module details from the Terraform Registry.
* Added support for Streamable HTTP, see [#99](https://github.com/hashicorp/terraform-mcp-server/pull/99)

IMPROVEMENTS

* Migrated to `stretchr/testify` for more robust test assertions and refactored test structure for maintainability.
* Improved and expanded README with installation, usage, and development instructions.
* Refined GitHub Actions workflows for more reliable builds, security scanning, and dependency management.
* Updated and pinned dependencies for improved reliability and security.
* Upgraded `mcp-go` from 0.27.0 to 0.32.0 to support streamable HTTP, update how tool arguments are accesseed. see [#99](https://github.com/hashicorp/terraform-mcp-server/pull/99)
* Updated e2e test to accomodate both stdio and HTTP mode, improve test report by adding test name and improve clean up process. see [#99](https://github.com/hashicorp/terraform-mcp-server/pull/99)

FIXES

- Fixed function names and improved documentation links for better usability.
- Addressed issues with CI security scanner and permissions.
- Corrected Go module name in `go.mod` for compatibility.

## 0.1.0 (May 20, 2025)

FEATURES

- First public release of Terraform MCP Server.
- Provides seamless integration with Terraform Registry APIs for provider and module discovery, documentation retrieval, and advanced IaC automation.
- Initial support for VS Code and Claude Desktop integration.
- Includes basic CI/CD, Docker build, and test infrastructure.
