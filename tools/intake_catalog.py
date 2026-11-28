"""Product/business discovery catalog: optional human context, not substitute for agent research."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Field:
    key: str
    label: str
    hint: str = ""


GROUPS: dict[str, tuple[Field, ...]] = {
    "Idea & problem": (
        Field("product.idea", "Product idea"),
        Field("product.primary_problem", "Customer pain"),
        Field("product.target_customer", "Target customers"),
        Field("product.existing_solution", "Existing product or MVP"),
        Field("product.constraints", "Important constraints"),
        Field("product.success_outcome", "Desired outcome"),
    ),
    "Customers & market": (
        Field("market.geography", "Target geographic market"),
        Field("market.customer_segment", "Primary customer segment"),
        Field("market.customer_evidence", "Customer interviews / problem evidence", "Enter sources or observations, not fabricated validation."),
        Field("market.competitors", "Known competitors or alternatives"),
        Field("market.market_restrictions", "Market or regulatory restrictions"),
    ),
    "Business model": (
        Field("business.value_proposition", "Core value proposition"),
        Field("business.revenue_model", "Preferred revenue model", "A preference is not an approved business model."),
        Field("business.cost_constraints", "Cost or funding constraints"),
        Field("business.success_metrics", "Success metrics / KPIs"),
    ),
    "MVP & product requirements": (
        Field("mvp.primary_journey", "Primary user journey"),
        Field("mvp.must_have", "MVP must-have capabilities"),
        Field("mvp.out_of_scope", "Explicitly out-of-scope features"),
        Field("mvp.launch_target", "Target launch date / milestone"),
        Field("mvp.resource_capacity", "Available team / implementation capacity"),
    ),
    "Pricing & validation": (
        Field("pricing.preferred_model", "Preferred pricing approach"),
        Field("pricing.expected_range", "Expected price range and currency"),
        Field("validation.riskiest_assumption", "Riskiest assumption to test"),
        Field("validation.available_evidence", "Existing experiments and outcomes"),
    ),
    "Go-to-market & roadmap": (
        Field("gtm.acquisition_channels", "Preferred acquisition channels"),
        Field("gtm.launch_market", "Initial go-to-market segment / geography"),
        Field("gtm.launch_budget", "GTM budget and constraints"),
        Field("roadmap.priority_outcomes", "Highest-priority product outcomes"),
        Field("roadmap.dependencies", "External milestones or dependencies"),
    ),
}

ALL_FIELDS = tuple(field for fields in GROUPS.values() for field in fields)
BY_KEY = {field.key: field for field in ALL_FIELDS}
