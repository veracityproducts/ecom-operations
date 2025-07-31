---
allowed-tools: Read, Grep, Glob, LS, WebSearch, WebFetch, Write, Edit, Agent, TodoWrite, TodoRead, Bash
description: Execute PRPs with dynamically created domain-specific agents from prp-create-adaptive
category: prp
---

# PRP Execute Adaptive - Domain-Agnostic Execution with Dynamic Agents

## Overview

Executes Persona Research Pipelines (PRPs) created by `/prp-create-adaptive`, leveraging the dynamically generated specialist agents for validation, implementation guidance, and quality assurance throughout the execution process.

## Usage

```bash
# Basic execution - uses agents created with the PRP
/prp-execute-adaptive --prp ./prp/feature_prp.md

# With validation level override
/prp-execute-adaptive --prp ./prp/complex_prp.md --validation-level 4

# Dry run mode to preview
/prp-execute-adaptive --prp ./prp/risky_prp.md --dry-run

# Skip specific validations
/prp-execute-adaptive --prp ./prp/prototype_prp.md --skip-validation performance

# With parallel task execution
/prp-execute-adaptive --prp ./prp/large_prp.md --parallel-tasks 5
```

## Parameters

- `--prp` (required): Path to PRP file to execute
- `--validation-level` (optional): Override validation depth (1-5)
  - Default: Uses PRP confidence score to auto-select
- `--skip-validation` (optional): Skip specific validation types
- `--dry-run` (optional): Preview changes without execution
- `--parallel-tasks` (optional): Number of parallel implementation tasks (default: 3)
- `--agent-dir` (optional): Override agent directory (default: ./agents/)

## Dynamic Agent Discovery

### Agent Location Resolution
```yaml
search_order:
  1. Project-level agents: ./agents/[domain]/
  2. Workspace agents: ../agents/[domain]/
  3. Global agents: ~/.claude/agents/[domain]/
  4. PRP-embedded agents: Extract from PRP metadata
  5. Coding specialists: Created dynamically by coding_doc_meta_agent
```

### Agent Loading Process
1. **Parse PRP Metadata**: Extract domain, agent list, complexity
2. **Initialize Coding Meta-Agent**: Always load coding_doc_meta_agent first
3. **Locate Agent Definitions**: Search in order listed above
4. **Load Agent Configurations**: Parse agent YAML/JSON files
5. **Create Technology Specialists**: coding_doc_meta_agent creates as needed
6. **Initialize Agent Network**: Create collaborative framework
7. **Validate Coverage**: Ensure all required specialists available

## Validation Levels with Dynamic Agents

### Level 1: Basic Syntax Validation
**Minimal agent involvement**
```bash
✓ Code compiles/interprets without errors
✓ Import statements resolve
✓ Basic structure validation

# Uses only technical implementation specialist for quick check
Agent: Use the [domain]-architecture-specialist agent to perform sanity check
```

### Level 2: Local Functionality
**Core specialist validation**
```bash
✓ Level 1 + 
✓ Services start successfully
✓ Basic functionality works
✓ Configuration valid

# Domain business expert validates core logic
Agent: Use the [domain]-business-expert agent to validate business rules

# Technical specialist checks implementation
Agent: Use the [implementation]-specialist agent to verify technical approach
```

### Level 3: Integration Testing
**Multi-specialist validation**
```bash
✓ Levels 1-2 +
✓ Unit tests pass
✓ Integration tests pass
✓ Cross-component validation

# All user advocates validate their personas
Agent: Use the persona-[role] agent to validate user journey

# Quality specialists check integration
Agent: Use the integration-testing-specialist agent to verify system cohesion
```

### Level 4: Production Readiness
**Comprehensive validation network**
```bash
✓ Levels 1-3 +
✓ Performance benchmarks met
✓ Security validated
✓ Compliance verified

# Full specialist team validation
Agent: Use the [domain]-compliance-specialist agent to verify regulatory compliance

Agent: Use the security-testing-specialist agent to validate security measures

Agent: Use the performance-specialist agent to confirm scalability
```

### Level 5: Enterprise Validation
**Complete specialist ecosystem**
```bash
✓ Levels 1-4 +
✓ Load testing passed
✓ Disaster recovery tested
✓ Stakeholder sign-off

# Every created specialist participates
[All domain business experts validate]
[All technical specialists verify]
[All user advocates confirm]
[All QA specialists certify]
```

## Implementation Process

### Phase 1: Pre-Implementation Analysis
```bash
# Initialize coding documentation meta-agent
Agent: Use the coding_doc_meta_agent agent to establish documentation research hierarchy

# Load dynamic agent team from PRP
Loading agent team for domain: [detected-domain]
✓ Found 12 specialist agents
✓ Agent configurations loaded
✓ Coding meta-agent ready for technology specialist creation
✓ Collaboration patterns established

# Meta-agent analyzes technology stack
Agent: Use the coding_doc_meta_agent agent to analyze required technologies and prepare specialist creation

# Specialists review implementation plan
Agent: Use the [lead-domain-expert] agent to validate approach

Agent: Use the [lead-technical-specialist] agent to confirm architecture
```

### Phase 2: Guided Implementation
```bash
# CRITICAL: Activate coding documentation meta-agent for all implementation
Agent: Use the coding_doc_meta_agent agent to establish documentation research hierarchy and create technology specialists

# Meta-agent ensures:
# 1. Reference projects checked first (remote-mcp-server, og-phonics, etc.)
# 2. MCP servers (context7, brightdata) checked second
# 3. Web searches only as last resort
# 4. Creates dynamic technology specialists as needed

# Task-by-task with specialist guidance
Implementing Task 1/N: [Task Description]

# Coding meta-agent creates technology specialists
Agent: Use the coding_doc_meta_agent agent to create [technology]-specialist for this implementation

# Domain specialists guide business logic
Agent: Use the [relevant-domain-specialist] agent to guide business requirements

# Example flow for payment gateway (fintech):
Task: Implement payment processing
Agent: Use the coding_doc_meta_agent agent to create nodejs-payment-specialist using MCP server patterns
Agent: Use the fintech-compliance-specialist agent to ensure PCI compliance
Agent: Use the payment-security-specialist agent to guide encryption
Agent: Use the fraud-detection-specialist agent to implement safeguards
```

### Phase 3: Progressive Validation
```bash
# After each component completion
Component: [Component Name]
✓ Implementation complete

# Domain-appropriate validation
Agent: Use the [domain-validator] agent to verify component

# Cross-functional validation
Agent: Use the integration-specialist agent to check compatibility
```

### Phase 4: Integration Validation
```bash
# End-to-end validation with user advocates
Agent: Use the persona-[primary-user] agent to validate full workflow

# Technical integration verification
Agent: Use the api-architecture-specialist agent to verify contracts

# Performance validation
Agent: Use the performance-optimization-specialist agent to confirm targets
```

### Phase 5: Final Certification
```bash
# Domain-specific certification
Agent: Use the [domain]-compliance-specialist agent to certify compliance

# Technical certification
Agent: Use the [lead-technical-specialist] agent to approve architecture

# Quality certification
Agent: Use the qa-lead-specialist agent to sign off on quality

✓ All specialists approve
✓ Confidence score: [X.X/10]
✓ Ready for deployment
```

## Domain-Specific Execution Examples

### Fintech Payment System
```bash
/prp-execute-adaptive --prp ./prp/payment_gateway_prp.md

# Automatically uses:
- fintech-compliance-specialist
- payment-security-specialist
- fraud-detection-specialist
- pci-validation-specialist
- financial-audit-specialist

# Includes validation for:
✓ PCI DSS compliance
✓ Transaction encryption
✓ Fraud detection rules
✓ Audit trail completeness
```

### Healthcare Patient Portal
```bash
/prp-execute-adaptive --prp ./prp/patient_portal_prp.md

# Automatically uses:
- hipaa-compliance-specialist
- clinical-workflow-specialist
- patient-experience-specialist
- medical-data-specialist
- healthcare-integration-specialist

# Includes validation for:
✓ HIPAA compliance
✓ Clinical data accuracy
✓ Patient privacy
✓ Medical workflow integration
```

### E-commerce Checkout
```bash
/prp-execute-adaptive --prp ./prp/checkout_optimization_prp.md

# Automatically uses:
- conversion-optimization-specialist
- payment-integration-specialist
- inventory-management-specialist
- customer-experience-specialist
- cart-abandonment-specialist

# Includes validation for:
✓ Conversion funnel optimization
✓ Payment security
✓ Inventory accuracy
✓ User experience flow
```

### SaaS Analytics Dashboard
```bash
/prp-execute-adaptive --prp ./prp/analytics_dashboard_prp.md

# Automatically uses:
- multi-tenant-specialist
- data-visualization-specialist
- performance-optimization-specialist
- dashboard-ux-specialist
- analytics-accuracy-specialist

# Includes validation for:
✓ Multi-tenant data isolation
✓ Visualization accuracy
✓ Query performance
✓ Real-time updates
```

## Progress Tracking

```
[████████████████████░░░░░░] 80% - Task 16/20: Implementing [component]

├─ Domain: [Detected Domain]
├─ Active Specialists: 4
├─ Completed: 15 tasks ✓
├─ In Progress: 1 task ([specialist] validating)
├─ Remaining: 4 tasks
├─ Validations Passed: 45/48
├─ Current Confidence: 8.7/10
└─ Estimated: 18 minutes remaining

Recent Specialist Feedback:
✓ [domain-expert]: "Business logic correctly implemented"
✓ [technical-specialist]: "Architecture patterns properly applied"
⚠️ [qa-specialist]: "Add error handling for edge case X"
```

## Error Recovery with Specialist Guidance

```bash
ERROR: [Component] failed validation

Agent: Use the [relevant-domain-expert] agent to diagnose issue

Specialist Analysis:
"The implementation doesn't account for [domain-specific requirement].
Required changes: [detailed guidance provided]"

Agent: Use the [implementation-specialist] agent to guide correction

[Implementation corrected with specialist guidance]
✓ Validation passed
```

## Output and Reporting

### Execution Report Format
```markdown
# Adaptive PRP Execution Report

**Project**: [Project Name]
**Domain**: [Detected Domain]
**Execution Time**: [Duration]
**Final Confidence**: [X.X/10]

## Dynamic Agent Team Performance
### Domain Business Experts (4 specialists)
✓ [specialist-1]: [Validation summary]
✓ [specialist-2]: [Validation summary]
[...]

### Technical Implementation (5 specialists)
✓ [specialist-1]: [Technical validation]
✓ [specialist-2]: [Architecture review]
[...]

### User Experience Advocates (3 specialists)
✓ persona-[role-1]: [User journey validation]
✓ persona-[role-2]: [Accessibility confirmation]
[...]

### Quality Assurance (4 specialists)
✓ [qa-specialist-1]: [Testing coverage]
✓ [qa-specialist-2]: [Security validation]
[...]

## Implementation Metrics
- Tasks Completed: [X/Y]
- Validation Level: [1-5]
- Domain Compliance: [Status]
- Technical Debt: [Assessment]
- Performance Targets: [Met/Exceeded]

## Specialist Recommendations
[Aggregated insights from all specialists]

## Certification Status
Lead Specialist Certification: [APPROVED/PENDING]
Domain Compliance: [VERIFIED/PENDING]
Production Readiness: [YES/NO]
```

## Agent Directory Structure

### Project-Level Agents
```
./agents/
├── fintech/
│   ├── fintech-compliance-specialist.yaml
│   ├── payment-security-specialist.yaml
│   └── fraud-detection-specialist.yaml
├── healthcare/
│   ├── hipaa-compliance-specialist.yaml
│   └── clinical-workflow-specialist.yaml
└── shared/
    ├── api-architecture-specialist.yaml
    └── security-testing-specialist.yaml
```

### Agent Definition Format
```yaml
name: fintech-compliance-specialist
domain: fintech
role: domain-expert
capabilities:
  - PCI DSS validation
  - Financial regulation compliance
  - Transaction audit requirements
validation_rules:
  - pattern: payment_processing
    requirements:
      - encryption_at_rest
      - encryption_in_transit
      - audit_logging
knowledge_base:
  - PCI DSS v4.0 standards
  - Financial industry regulations
  - Compliance best practices
```

## Integration with Adaptive System

### Seamless Workflow
```bash
# Create adaptive PRP with dynamic agents
/prp-create-adaptive --spec ./specs/feature.md

# Execute with created agents
/prp-execute-adaptive --prp ./prp/feature_prp.md

# Analyze results
/analyze-prp-results --execution ./metrics/feature_execution.json
```

### Agent Evolution
- Successful execution patterns improve agent definitions
- Failed validations refine agent rules
- Cross-domain patterns enhance shared specialists

## Best Practices

### 1. Trust Dynamic Agents
- Agents are created specifically for your domain
- Their knowledge is tailored to your requirements
- Specialist consensus indicates high confidence
- Coding meta-agent ensures proper documentation research

### 2. Leverage Coding Meta-Agent
- Always activates for implementation tasks
- Creates technology-specific specialists dynamically
- Follows strict research hierarchy (reference → MCP → web)
- Reuses proven patterns from reference projects

### 3. Respect Validation Levels
- Don't skip levels for production systems
- Higher complexity requires higher validation
- Enterprise systems always need Level 5

### 4. Monitor Specialist Feedback
- Address warnings immediately
- Track confidence scores
- Document specialist insights
- Pay special attention to technology specialist recommendations

### 5. Maintain Agent Libraries
- Save successful agent teams
- Build domain-specific collections
- Share agents across projects
- Technology specialists can be reused across similar stacks

### 6. Leverage Parallelism
- Use `--parallel-tasks` for large PRPs
- Specialists can validate in parallel
- Reduces overall execution time

## Troubleshooting

### Missing Agents
```bash
ERROR: Cannot find agent [specialist-name]

Solutions:
1. Check agent directory paths
2. Verify PRP includes agent definitions
3. Use --agent-dir to specify location
4. Run prp-create-adaptive to regenerate
```

### Validation Failures
```bash
ERROR: Specialist [name] validation failed

Solutions:
1. Review specialist feedback
2. Check domain requirements
3. Verify implementation matches PRP
4. Consult relevant documentation
```

### Performance Issues
```bash
WARNING: Execution taking longer than expected

Solutions:
1. Increase --parallel-tasks
2. Skip non-critical validations
3. Use lower validation level for dev
4. Profile bottleneck specialists
```

---

*This adaptive execution system provides domain-agnostic PRP execution with the same quality and depth as domain-specific implementations, leveraging dynamically created specialist teams for optimal validation and guidance.*