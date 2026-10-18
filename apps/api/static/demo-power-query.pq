// Synthetic demo only. Paste into a Blank Query in Excel Power Query or Power BI Desktop.
// Refresh re-reads the demo API. This is not a live marketplace connector.
let
    Source = Json.Document(Web.Contents("http://localhost:8000", [RelativePath="api/v1/demo/business/report"])),
    AssertDemo = if Source[demo] = true then Source[rows] else error "This query is only for synthetic demo data.",
    Rows = Table.FromRecords(AssertDemo),
    Marked = Table.AddColumn(Rows, "data_mode", each "DEMO", type text),
    Selected = Table.SelectColumns(Marked, {"data_mode", "business_date", "channel", "shop_id", "order_id", "sku", "currency", "net_revenue", "cogs", "known_costs", "profit_actual", "profit_provisional", "confidence", "expected_payout", "actual_payout", "payout_difference", "reconciliation"}),
    Types = Table.TransformColumnTypes(Selected, {{"business_date", type date}, {"net_revenue", Currency.Type}, {"cogs", Currency.Type}, {"known_costs", Currency.Type}, {"profit_actual", Currency.Type}, {"profit_provisional", Currency.Type}, {"expected_payout", Currency.Type}, {"actual_payout", Currency.Type}, {"payout_difference", Currency.Type}}, "en-US")
in
    Types