// Copyright (c) HashiCorp, Inc.
// SPDX-License-Identifier: MPL-2.0

package tools

import (
	"context"
	"encoding/json"
	"fmt"
	"net/url"
	"strings"

	"github.com/hashicorp/terraform-mcp-server/pkg/client"
	"github.com/hashicorp/terraform-mcp-server/pkg/utils"
	log "github.com/sirupsen/logrus"

	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"
)

func SearchPolicies(logger *log.Logger) server.ServerTool {
	return server.ServerTool{
		Tool: mcp.NewTool("search_policies",
			mcp.WithDescription(`Searches for Terraform policies based on a query string.
This tool returns a list of matching policies, which can be used to retrieve detailed policy information using the 'get_policy_details' tool.
You MUST call this function before 'get_policy_details' to obtain a valid terraform_policy_id.
When selecting the best match, consider the following:
	- Name similarity to the query
	- Title relevance
	- Verification status (verified)
	- Download counts (popularity)
Return the selected policyID and explain your choice. If there are multiple good matches, mention this but proceed with the most relevant one.
If no policies were found, reattempt the search with a new policy_query.`),
			mcp.WithTitleAnnotation("Search and match Terraform policies based on name and relevance"),
			mcp.WithOpenWorldHintAnnotation(true),
			mcp.WithReadOnlyHintAnnotation(true),
			mcp.WithDestructiveHintAnnotation(false),
			mcp.WithString("policy_query",
				mcp.Required(),
				mcp.Description("The query to search for Terraform modules."),
			),
		),
		Handler: func(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
			return getSearchPoliciesHandler(ctx, request, logger)
		},
	}
}

func getSearchPoliciesHandler(ctx context.Context, request mcp.CallToolRequest, logger *log.Logger) (*mcp.CallToolResult, error) {
	var terraformPolicies client.TerraformPolicyList
	pq, err := request.RequireString("policy_query")
	if err != nil {
		return nil, utils.LogAndReturnError(logger, "required input: policy_query is required", err)
	}
	if pq == "" {
		return nil, utils.LogAndReturnError(logger, "required input: policy_query cannot be empty", nil)
	}
	pq = strings.ToLower(pq)

	// Get a simple http client to access the public Terraform registry from context
	httpClient, err := client.GetHttpClientFromContext(ctx, logger)
	if err != nil {
		logger.WithError(err).Error("failed to get http client for public Terraform registry")
		return mcp.NewToolResultError(fmt.Sprintf("failed to get http client for public Terraform registry: %v", err)), nil
	}
	uri := (&url.URL{
		Path: "policies",
		RawQuery: url.Values{
			"page[size]": {"100"}, // static list of 100 is fine for now
			"include":    {"latest-version"},
		}.Encode(),
	}).String()
	policyResp, err := client.SendRegistryCall(httpClient, "GET", uri, logger, "v2")
	if err != nil {
		return nil, utils.LogAndReturnError(logger, "fetching policies: registry API did not return a successful response", err)
	}

	err = json.Unmarshal(policyResp, &terraformPolicies)
	if err != nil {
		return nil, utils.LogAndReturnError(logger, "unmarshalling policy list", err)
	}

	var builder strings.Builder
	builder.WriteString(fmt.Sprintf("Matching Terraform Policies for query: %s\n\n", pq))
	builder.WriteString("Each result includes:\n- terraform_policy_id: Unique identifier to be used with get_policy_details tool\n- Name: Policy name\n- Title: Policy description\n- Downloads: Policy downloads\n---\n\n")

	contentAvailable := false
	for _, policy := range terraformPolicies.Data {
		cs, err := utils.ContainsSlug(strings.ToLower(policy.Attributes.Title), pq)
		cs_pn, err_pn := utils.ContainsSlug(strings.ToLower(policy.Attributes.Name), pq)
		if (cs || cs_pn) && err == nil && err_pn == nil {
			contentAvailable = true
			ID := strings.ReplaceAll(policy.Relationships.LatestVersion.Links.Related, "/v2/", "")
			builder.WriteString(fmt.Sprintf(
				"- terraform_policy_id: %s\n- Name: %s\n- Title: %s\n- Downloads: %d\n---\n",
				ID,
				policy.Attributes.Name,
				policy.Attributes.Title,
				policy.Attributes.Downloads,
			))
		}
	}

	policyData := builder.String()
	if !contentAvailable {
		errMessage := fmt.Sprintf("finding policies, none found matching the query: %s. Try a different policy_query.", pq)
		return nil, utils.LogAndReturnError(logger, errMessage, nil)
	}

	return mcp.NewToolResultText(policyData), nil
}
