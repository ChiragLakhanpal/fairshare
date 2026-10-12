# Hosting the harness in Microsoft Foundry

The agent in `harness/agent.py` runs unchanged on a laptop and as a Foundry Hosted Agent. The host wrapper is
`harness/foundry/host.py` (`ResponsesHostServer`), the container is `harness/foundry/Dockerfile`.

Steps (from the Foundry hosted-agent quickstart, checked Oct 11, 2026; `azd` 1.27.1 or later, Owner on the resource group):

```
azd ext install azure.ai.agents
azd ai agent init -m harness/foundry/agent.yaml      # generates/validates the manifest; pick the Python Responses template
azd ai agent run                                      # local run of the container
azd provision                                         # Foundry instance, project, model deployment (gpt-4.1-mini), App Insights, container registry
azd deploy
azd ai agent invoke "How did Summit Travel Partners do on DFW to ORD in Q3 2026 versus Q3 2025?"
```

Environment the hosted agent needs (set as secrets in the Foundry project, never in the image): `DATABRICKS_HOST`,
`DATABRICKS_SERVER_HOSTNAME`, `DATABRICKS_HTTP_PATH`, `DATABRICKS_TOKEN` (a personal token; Genie as a user is free,
as a service principal it is billed), `GENIE_SPACE_ID`, `AZURE_OPENAI_*` or managed identity for the model.

What is real and what is not: the hosted agent, the model deployment, the traces are real on the Azure free credit.
Copilot Studio in Teams and Fabric need a work tenant and stay on the diagram as the next step.

If the free-trial quota for gpt-4.1-mini is zero (the quota page shows TPM per model), point `FAIRSHARE_MODEL=databricks`
at a Databricks serving endpoint; the hosted agent still runs in Foundry and calls the model over the network.
