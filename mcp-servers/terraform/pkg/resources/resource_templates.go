// Copyright (c) HashiCorp, Inc.
// SPDX-License-Identifier: MPL-2.0

package resources

import (
	"context"
	"fmt"
	"net/http"
	"path"

	"github.com/hashicorp/terraform-mcp-server/pkg/client"
	"github.com/hashicorp/terraform-mcp-server/pkg/utils"
	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"
	log "github.com/sirupsen/logrus"
)

func RegisterResourceTemplates(hcServer *server.MCPServer, logger *log.Logger) {
	hcServer.AddResourceTemplate(
		providerResourceTemplate(
			path.Join(utils.PROVIDER_BASE_PATH, "{namespace}", "name", "{name}", "version", "{version}"),
			"Provider details",
			logger,
		),
	)
}

func providerResourceTemplate(resourceURI string, description string, logger *log.Logger) (mcp.ResourceTemplate, server.ResourceTemplateHandlerFunc) {
	return mcp.NewResourceTemplate(
			resourceURI,
			description,
			mcp.WithTemplateDescription("Describes details for a Terraform provider"),
			mcp.WithTemplateMIMEType("application/json"),
			// TODO: Add pagination parameters here using the correct mcp-go mechanism
			// Example (conceptual):
			// mcp.WithInteger("page_number", mcp.Description("Page number"), mcp.Optional()),
			// mcp.WithInteger("page_size", mcp.Description("Page size"), mcp.Optional()),
		),
		func(ctx context.Context, request mcp.ReadResourceRequest) ([]mcp.ResourceContents, error) {
			logger.Infof("Provider resource template - resourceURI: %s", request.Params.URI)

			// Get a simple http client to access the public Terraform registry from context
			httpClient, err := client.GetHttpClientFromContext(ctx, logger)
			if err != nil {
				return nil, utils.LogAndReturnError(logger, "getting http client for public Terraform registry", err)
			}
			providerDocs, err := providerResourceTemplateHelper(httpClient, request.Params.URI, logger)
			if err != nil {
				return nil, utils.LogAndReturnError(logger, "getting provider details for resource template", err)
			}
			resourceContents := make([]mcp.ResourceContents, 1)
			resourceContents[0] = mcp.TextResourceContents{
				MIMEType: "text/markdown",
				URI:      resourceURI,
				Text:     providerDocs,
			}
			return resourceContents, err
		}
}

// providerResourceTemplateHelper fetches the provider details based on the resource URI
func providerResourceTemplateHelper(httpClient *http.Client, resourceURI string, logger *log.Logger) (string, error) {
	namespace, name, version, err := utils.ExtractProviderNameAndVersion(resourceURI)
	if err != nil {
		return "", utils.LogAndReturnError(logger, "extracting provider name and version", err)
	}
	logger.Debugf("Extracted namespace: %s, name: %s, version: %s", namespace, name, version)

	if version == "" || version == "latest" || !utils.IsValidProviderVersionFormat(version) {
		version, err = client.GetLatestProviderVersion(httpClient, namespace, name, logger)
		if err != nil {
			return "", utils.LogAndReturnError(logger, fmt.Sprintf("getting %s/%s latest provider version for resource template", namespace, name), err)
		}
	}

	providerVersionUri := path.Join(utils.PROVIDER_BASE_PATH, namespace, "name", name, "version", version)
	logger.Debugf("Provider resource template - providerVersionUri: %s", providerVersionUri)
	if err != nil {
		return "", utils.LogAndReturnError(logger, "getting provider details for resource template", err)
	}

	// Get the provider-version-id for the specified provider version
	providerVersionID, err := client.GetProviderVersionID(httpClient, namespace, name, version, logger)
	logger.Debugf("Provider resource template - Provider version id providerVersionID: %s, providerVersionUri: %s", providerVersionID, providerVersionUri)
	if err != nil {
		return "", utils.LogAndReturnError(logger, "getting provider details for provider-version-id", err)
	}

	// Get all the docs based on provider version id
	providerDocs, err := client.GetProviderOverviewDocs(httpClient, providerVersionID, logger)
	logger.Debugf("Provider resource template - Provider docs providerVersionID: %s", providerVersionID)
	if err != nil {
		return "", utils.LogAndReturnError(logger, "getting provider details for docs with provider-version-id", err)
	}

	// Only return the provider overview
	return providerDocs, nil
}
