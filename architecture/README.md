# System Architecture Diagrams

This folder is designed to store structural topology layouts. You can copy the Mermaid script below into [Mermaid Live Editor](https://mermaid.live/) to generate a high-definition image layout to save in this directory.

## Mermaid System Architecture Layout:

```mermaid
graph TD
    %% Styling
    classDef client fill:#EAEAEA,stroke:#222,stroke-width:2.5px;
    classDef lb fill:#FFD000,stroke:#222,stroke-width:2.5px;
    classDef srv fill:#FFFFFF,stroke:#222,stroke-width:2.5px;
    classDef db fill:#FFF6CC,stroke:#222,stroke-width:2.5px;
    
    %% Nodes
    C[Users / Clients]:::client
    LB[BalancePro Load Balancer]:::lb
    HM[Health Monitor Daemon]:::lb
    DB[(SQLite database.db)]:::db
    
    subgraph Pool [Server Pool]
        S1[Server 1 - Alpha]:::srv
        S2[Server 2 - Beta]:::srv
        S3[Server 3 - Gamma]:::srv
        S4[Server 4 - Delta]:::srv
    end
    
    %% Flows
    C -->|POST /request| LB
    LB -->|Least Connections Routing| Pool
    HM -.->|Pings every 5s| Pool
    HM -->|Logs status| DB
    LB -->|Logs traffic & metrics| DB
```
