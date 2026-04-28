# C4 Container Diagram

Render: https://www.plantuml.com/plantuml/uml

```plantuml
@startuml

!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Container.puml

skinparam defaultFontSize 13
skinparam nodesep 55
skinparam ranksep 80

HIDE_STEREOTYPE()
LAYOUT_TOP_DOWN()

AddElementTag("svc",   $bgColor="#1168bd", $fontColor="#ffffff", $borderColor="#0d52a0")
AddElementTag("topic", $bgColor="#c0392b", $fontColor="#ffffff", $borderColor="#96281b")
AddElementTag("db",    $bgColor="#b7550a", $fontColor="#ffffff", $borderColor="#8c4008")

' ── Actors ───────────────────────────────────────────────────────────────────
Person_Ext(client,  "Bank Client")
Person(analyst, "Bank Analyst")

' ── Layer 1: Kafka ───────────────────────────────────────────────────────────
System_Boundary(kafka, "Apache Kafka · KRaft") {
    together {
        Container(t_raw,  "tx.raw",        "topic", "raw events",     $tags="topic")
        Container(t_alrt, "alerts",         "topic", "fraud alerts",   $tags="topic")
        Container(t_lim,  "limit_exceeded", "topic", "limit breaches", $tags="topic")
    }
}

' ── Layer 2: Microservices ───────────────────────────────────────────────────
System_Boundary(svcs, "Microservices") {
    together {
        Container(tx,    "transaction-service", ":8000", "entry point",    $tags="svc")
        Container(fraud, "fraud-detector",      ":8001", "7 rules, 0–100", $tags="svc")
        Container(lim,   "limits-service",      ":8002", "spending limits", $tags="svc")
        Container(notify,"notify-service",      ":8003", "webhooks",        $tags="svc")
        Container(admin, "admin-api",           ":8004", "JWT · CRUD",      $tags="svc")
    }
}

' ── Layer 3: PostgreSQL schemas (one per service) ────────────────────────────
System_Boundary(pg, "PostgreSQL 16") {
    together {
        ContainerDb(s_tx,    "transactions", "schema", "", $tags="db")
        ContainerDb(s_fraud, "fraud",        "schema", "", $tags="db")
        ContainerDb(s_lim,   "limits",       "schema", "", $tags="db")
        ContainerDb(s_notif, "notify",       "schema", "", $tags="db")
        ContainerDb(s_auth,  "auth",         "schema", "", $tags="db")
    }
}

' ── Layer ordering ───────────────────────────────────────────────────────────
Lay_D(kafka, svcs)
Lay_D(svcs,  pg)

' ── Horizontal ordering ──────────────────────────────────────────────────────
Lay_R(t_raw,  t_alrt)
Lay_R(t_alrt, t_lim)

Lay_R(tx,    fraud)
Lay_R(fraud, lim)
Lay_R(lim,   notify)
Lay_R(notify, admin)

Lay_R(s_tx,    s_fraud)
Lay_R(s_fraud, s_lim)
Lay_R(s_lim,   s_notif)
Lay_R(s_notif, s_auth)

' ── Actor positions ──────────────────────────────────────────────────────────
Lay_L(tx,    client)
Lay_R(admin, analyst)

' ── Actors → Services ────────────────────────────────────────────────────────
Rel_R(client,  tx,    "POST /transactions")
Rel_L(analyst, admin, " ")

' ── Services → Kafka (publish, up) ──────────────────────────────────────────
Rel_U(tx,    t_raw,  "publish")
Rel_U(fraud, t_alrt, "publish")
Rel_U(lim,   t_lim,  "publish")

' ── Kafka → Services (consume, down) ─────────────────────────────────────────
Rel_D(t_raw,  fraud,  "consume")
Rel_D(t_raw,  lim,    "consume")
Rel_D(t_alrt, notify, "consume")
Rel_D(t_lim,  notify, "consume")

' ── Services → own DB (down) ─────────────────────────────────────────────────
Rel_D(tx,    s_tx,    " ")
Rel_D(fraud, s_fraud, " ")
Rel_D(lim,   s_lim,   " ")
Rel_D(notify,s_notif, " ")
Rel_D(admin, s_auth,  " ")

' ── Admin manages other schemas ──────────────────────────────────────────────
Rel_D(admin, s_fraud, "rules")
Rel_D(admin, s_lim,   "limits")

@enduml
```
