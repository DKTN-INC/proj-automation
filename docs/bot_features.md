# Bot Features Documentation

This document describes the budget and marketing features available in the Project Automation Discord Bot.

## Budget Features

The budget module provides functionality for budget tracking and spending categorization.

### Functions

#### `summarize_budget(transactions, limit)`

Summarizes budget information based on transaction data and a spending limit.

**Parameters:**
- `transactions` (List[Dict]): List of transaction dictionaries with 'amount' key
- `limit` (Decimal/float/int): Budget limit

**Returns:**
- `BudgetSummary`: Dataclass containing:
  - `totals` (Decimal): Total amount spent
  - `remaining` (Decimal): Remaining budget amount  
  - `percent_used` (float): Percentage of budget used (rounded to 1 decimal place)
  - `status` (str): Budget status ("unused", "under_budget", "on_track", "warning", "over_budget")

**Status Thresholds:**
- `unused`: 0% used
- `under_budget`: < 50% used
- `on_track`: 50-79% used
- `warning`: 80-99% used
- `over_budget`: ≥ 100% used

**Example:**
```python
from bot.features.budget import summarize_budget

transactions = [
    {'amount': 150.75},
    {'amount': 200.50},
    {'amount': 99.25}
]

summary = summarize_budget(transactions, 1000)
print(f"Total spent: ${summary.totals}")
print(f"Remaining: ${summary.remaining}")
print(f"Usage: {summary.percent_used}%")
print(f"Status: {summary.status}")
```

#### `categorize_spend(items, category_key="category", amount_key="amount")`

Categorizes and aggregates spending by category.

**Parameters:**
- `items` (List[Dict]): List of spending items
- `category_key` (str): Key name for category in item dictionaries (default: "category")
- `amount_key` (str): Key name for amount in item dictionaries (default: "amount")

**Returns:**
- `Dict[str, Decimal]`: Dictionary mapping category names to aggregated amounts (rounded to 2 decimal places)

**Example:**
```python
from bot.features.budget import categorize_spend

items = [
    {'category': 'Food', 'amount': 150.75},
    {'category': 'Transport', 'amount': 50.25},
    {'category': 'Food', 'amount': 75.50},
    {'category': 'Office', 'amount': 200.00}
]

categories = categorize_spend(items)
for category, total in categories.items():
    print(f"{category}: ${total}")

# Custom keys example
custom_items = [
    {'type': 'Marketing', 'cost': 500},
    {'type': 'Equipment', 'cost': 1200}
]
custom_categories = categorize_spend(custom_items, category_key='type', amount_key='cost')
```

## Marketing Features

The marketing module provides functionality for creating and managing marketing campaign briefs.

### Functions

#### `generate_campaign_brief(...)`

Generates a comprehensive campaign brief with the provided information.

**Parameters:**
- `campaign_name` (str): Name of the marketing campaign
- `target_audience` (str): Description of the target audience
- `objectives` (List[str]): List of campaign objectives
- `budget` (Optional[float]): Campaign budget (default: None)
- `timeline` (Optional[str]): Timeline description (default: None)
- `channels` (Optional[List[str]]): List of marketing channels (default: empty list)
- `key_messages` (Optional[List[str]]): List of key marketing messages (default: empty list)
- `success_metrics` (Optional[List[str]]): List of success metrics (default: empty list)

**Returns:**
- `CampaignBrief`: Dataclass containing all campaign information with `created_at` timestamp

**Example:**
```python
from bot.features.marketing import generate_campaign_brief

brief = generate_campaign_brief(
    campaign_name="Summer Sale 2024",
    target_audience="Existing customers aged 25-45",
    objectives=[
        "Increase sales by 30%",
        "Clear summer inventory",
        "Boost brand engagement"
    ],
    budget=75000.0,
    timeline="June 1 - August 31, 2024",
    channels=["Email", "Social Media", "Google Ads", "Display Ads"],
    key_messages=[
        "Save up to 50% on summer essentials",
        "Limited time offer - shop now",
        "Free shipping on orders over $50"
    ],
    success_metrics=[
        "30% increase in monthly sales",
        "75% inventory clearance rate",
        "25% increase in email engagement"
    ]
)
```

#### `render_campaign_brief_markdown(brief)`

Renders a campaign brief as formatted Markdown.

**Parameters:**
- `brief` (CampaignBrief): Campaign brief to render

**Returns:**
- `str`: Formatted Markdown string

**Example:**
```python
from bot.features.marketing import render_campaign_brief_markdown

markdown_output = render_campaign_brief_markdown(brief)
print(markdown_output)
```

**Sample Output:**
```markdown
# Summer Sale 2024

## Target Audience
Existing customers aged 25-45

## Objectives
- Increase sales by 30%
- Clear summer inventory
- Boost brand engagement

## Budget
$75,000.00

## Timeline
June 1 - August 31, 2024

## Marketing Channels
- Email
- Social Media
- Google Ads
- Display Ads

## Key Messages
- Save up to 50% on summer essentials
- Limited time offer - shop now
- Free shipping on orders over $50

## Success Metrics
- 30% increase in monthly sales
- 75% inventory clearance rate
- 25% increase in email engagement

## Created
2024-06-15 14:30:25
```

## Discord Bot Integration

These features are designed to be easily integrated into Discord slash commands. Here are examples of how they might be used:

### Budget Command Example

```python
@bot.tree.command(name='budget', description='Analyze budget and spending')
async def budget_command(interaction: discord.Interaction, 
                        transactions_file: discord.Attachment,
                        budget_limit: float):
    # Parse transactions from uploaded file
    # Use summarize_budget() and categorize_spend()
    # Send formatted response
    pass
```

### Marketing Command Example

```python
@bot.tree.command(name='marketing', description='Generate marketing campaign brief')
async def marketing_command(interaction: discord.Interaction,
                           campaign_name: str,
                           target_audience: str,
                           objectives: str):
    # Parse objectives from string
    # Use generate_campaign_brief()
    # Use render_campaign_brief_markdown()
    # Send as formatted message or file
    pass
```

## Error Handling

Both modules are designed with robust error handling:

- **Budget functions**: Handle missing amounts/categories gracefully with defaults
- **Marketing functions**: All optional parameters have sensible defaults
- **Decimal precision**: Budget calculations use Decimal for financial accuracy
- **Type safety**: Functions validate and convert input types appropriately

## Dependencies

These features use only standard library modules:
- `dataclasses`: For structured data containers
- `typing`: For type hints  
- `decimal`: For precise financial calculations
- `datetime`: For timestamps

No external dependencies are required, making integration simple and lightweight.