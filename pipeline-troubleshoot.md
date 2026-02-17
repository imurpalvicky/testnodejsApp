Phase 1: IDE Triage & Responsible Team Fork
1. The Trigger & Context Gathering

A Jenkins pipeline fails.

The developer asks their Custom Agent in the IDE to investigate.

The Custom Agent fetches the sanitized pipeline logs, environment metadata, and active Shared Library version via the MCP Server.

2. The Classification & Knowledge Query

The Agent analyzes the stack trace and classifies the Responsible Team (app, devops, dba, mw, cloudops, platform).

It queries the Known Error Database (KEDB) for any proven fixes associated with the error signature.

3. The Responsible Team Fork
The Agent routes the workflow based strictly on the classified team:

Path A (Application Team): If the classification is app, the root cause lies in code owned by the developers (whether that is application source code, unit tests, or app-owned configuration files). The Agent automatically helps the developer write the fix, test it locally, and push the change. (No ServiceNow ticket required).

Path B (Other Teams): If the classification is devops, dba, mw, or any other infrastructure team, the Agent stops. It will not attempt to write code for systems outside the Application Team's ownership.

4. The ServiceNow Template & Catalogue Generation
For Path B, the Agent provides the developer with exactly what they need to route the issue:

Catalogue Information: The Agent specifies exactly which ServiceNow catalogue item to use (e.g., "Please use the 'DevOps CI/CD Incident' catalogue item").

Template Data: The Agent generates the markdown template containing the LLM-analyzed failed_state, root_cause, and the KEDB proven fix (if one exists).

Manual Handoff: The developer manually navigates to the specified ServiceNow catalogue, pastes the generated template, and submits the ticket.


Phase 2: Autonomous DevOps Remediation
Goal: Headless execution of infrastructure fixes with mandatory Human-in-the-Loop (HITL) review and continuous learning.

1. The ServiceNow Listener

A background service polls the ServiceNow REST API every 5 minutes.

It looks for tickets in the New state assigned to the DevOps queue.

2. The Fast-Track Execution (DevOps Agent)

The listener passes the ServiceNow ticket payload to the standalone DevOps AI Agent.

Because the Phase 1 Agent already embedded the exact KEDB proven fix in the ticket, the DevOps Agent immediately checks out a feature branch in the Config Repo.

It applies the specific property change to the protected file.

3. Security Scanning & Pull Request

The Agent runs a local secret-scan on the staged diff to ensure no credentials are hardcoded.

The Agent pushes the branch and raises a Pull Request against the protected master branch.

It updates the ServiceNow incident status to In Progress and adds a work note linking to the PR.

4. Human-in-the-Loop (HITL) Validation

The PR is blocked until a human DevOps Engineer reviews it.

If the code is sound, the DevOps Engineer approves and merges the PR.

5. Resolution & Closure

The merge triggers the CI/CD pipeline.

The DevOps Engineer monitors the pipeline. If it passes, they update the ServiceNow ticket to Resolved.

The Application Team (the original requester) validates their deployment is successful and marks the ticket as Closed.

6. The Learning Loop (KEDB Harvest)

If the DevOps Engineer had to modify the Agent's fix, or if this was a completely novel issue, they apply a label (e.g., KEDB-Promote) to the merged PR.


graph TD
    classDef phase1 fill:#e1f5fe,stroke:#01579b,stroke-width:2px;
    classDef phase2 fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px;
    classDef human fill:#fff3e0,stroke:#e65100,stroke-width:2px;
    classDef database fill:#f3e5f5,stroke:#4a148c,stroke-width:2px;

    %% TRIGGER
    Start([🔴 Jenkins Pipeline Fails]) --> AskAgent[Dev asks IDE Custom Agent]
    
    %% PHASE 1: IDE & MCP
    subgraph Phase 1: IDE Triage & Classification
        AskAgent --> MCP[Agent uses MCP Server]
        MCP --> Fetch[Fetch Logs, Metadata & Query KEDB]
        Fetch --> Classify{Identify Responsible Team}

        Classify -- Path A: App Team Issue --> AppFix[Agent helps Dev fix app code or app-config]
        AppFix --> DevPush[Dev commits & pushes] --> EndApp([✅ Resolved])

        Classify -- Path B: Other Team Issue --> GenTemplate[Agent generates SNOW Template & Catalogue Info]
    end
    class AskAgent,MCP,Fetch,Classify,AppFix,ConfigFix,GenTemplate phase1;

    %% THE BRIDGE
    GenTemplate --> CreateSNOW[🧑‍💻 Dev uses Catalogue Info to manually create ServiceNow Incident]
    class CreateSNOW human;

    %% PHASE 2: AUTONOMOUS REMEDIATION
    CreateSNOW --> Poller((5-Min Poller))
    
    subgraph Phase 2: Autonomous DevOps Remediation
        Poller --> SNOWTicket{New Ticket in DevOps Queue?}
        SNOWTicket -- Yes --> DevopsAgent[DevOps AI Agent reads ticket & KEDB fix]
        DevopsAgent --> ApplyFix[Agent checks out Config Repo & applies fix]
        ApplyFix --> Scan[Agent runs local secret-scan]
        Scan --> RaisePR[Agent raises PR against protected branch]
        RaisePR --> UpdateSNOW[Agent updates ticket: 'In Progress']
    end
    class Poller,SNOWTicket,DevopsAgent,ApplyFix,Scan,RaisePR,UpdateSNOW phase2;

    %% HUMAN REVIEW & CLOSURE
    UpdateSNOW --> HumanReview{🧑‍🔧 DevOps Engineer PR Review}
    class HumanReview human;

    HumanReview -- Approved & Merged --> RunPipeline[CI/CD Pipeline Runs]
    HumanReview -- Rejected / Modified --> ManualFix[Human fixes manually]
    
    RunPipeline --> ValidateDevOps[🧑‍🔧 DevOps validates & sets 'Resolved']
    ValidateDevOps --> ValidateApp[🧑‍💻 App Team validates & sets 'Closed']
    ValidateApp --> CloseSNOW([✅ Incident Closed])
    class ValidateDevOps,ValidateApp human;

    %% THE LEARNING LOOP (KEDB)
    RunPipeline --> KEDBPromote{PR Tagged 'KEDB-Promote'?}
    ManualFix --> KEDBPromote
    KEDBPromote -- Yes --> BatchJob[Daily Batch Job extracts error & diff]
    BatchJob --> UpdateKEDB[(Update Known Error Database)]
    UpdateKEDB -. Enhances future triage .-> Fetch
    class UpdateKEDB database;

A daily batch job scrapes all PRs with this label, extracts the diff and the error signature, and writes a new entry into the KEDB
