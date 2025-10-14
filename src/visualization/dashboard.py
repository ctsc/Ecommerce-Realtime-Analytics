"""
Real-time analytics dashboard using Plotly Dash.
Displays key metrics, fraud alerts, and customer insights.
"""

import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta

from src.storage.database import db_manager
from src.utils.config import config
from src.utils.metrics import metrics_collector
from src.utils.logging_config import get_logger


logger = get_logger(__name__)


# Initialize Dash app with Bootstrap theme
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.CYBORG],
    suppress_callback_exceptions=True
)

app.title = "E-Commerce Real-Time Analytics"


# App layout
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H1(
                "🛍️ E-Commerce Real-Time Analytics Dashboard",
                className="text-center mb-4 mt-4",
                style={"color": "#00d9ff"}
            ),
        ])
    ]),
    
    # Key Metrics Cards
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("Total Transactions", className="card-title"),
                    html.H2(id="metric-total-transactions", children="0",
                           style={"color": "#00d9ff"}),
                    html.P("Last updated: ", className="card-text"),
                    html.P(id="metric-last-update", className="card-text")
                ])
            ], color="dark", className="mb-3")
        ], width=3),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("Throughput", className="card-title"),
                    html.H2(id="metric-throughput", children="0 tx/s",
                           style={"color": "#00ff88"}),
                    html.P("Transactions per second", className="card-text")
                ])
            ], color="dark", className="mb-3")
        ], width=3),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("Fraud Detected", className="card-title"),
                    html.H2(id="metric-fraud-count", children="0",
                           style={"color": "#ff4444"}),
                    html.P(id="metric-fraud-rate", children="0% fraud rate",
                          className="card-text")
                ])
            ], color="dark", className="mb-3")
        ], width=3),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("Data Quality", className="card-title"),
                    html.H2(id="metric-quality-score", children="100%",
                           style={"color": "#ffaa00"}),
                    html.P("Quality score", className="card-text")
                ])
            ], color="dark", className="mb-3")
        ], width=3),
    ]),
    
    # Graphs Row 1
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("Transaction Volume (Real-Time)", className="card-title"),
                    dcc.Graph(id="graph-transaction-volume")
                ])
            ], color="dark", className="mb-3")
        ], width=6),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("Revenue by Category", className="card-title"),
                    dcc.Graph(id="graph-revenue-by-category")
                ])
            ], color="dark", className="mb-3")
        ], width=6),
    ]),
    
    # Graphs Row 2
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("Fraud Detection Over Time", className="card-title"),
                    dcc.Graph(id="graph-fraud-over-time")
                ])
            ], color="dark", className="mb-3")
        ], width=6),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("Customer Segmentation", className="card-title"),
                    dcc.Graph(id="graph-customer-segments")
                ])
            ], color="dark", className="mb-3")
        ], width=6),
    ]),
    
    # Recent Fraud Alerts Table
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("⚠️ Recent Fraud Alerts", className="card-title"),
                    html.Div(id="fraud-alerts-table")
                ])
            ], color="dark", className="mb-3")
        ])
    ]),
    
    # Auto-refresh interval
    dcc.Interval(
        id='interval-component',
        interval=config.dashboard.refresh_interval,  # milliseconds
        n_intervals=0
    )
    
], fluid=True, style={"backgroundColor": "#1a1a1a"})


# Callbacks for updating dashboard
@app.callback(
    [
        Output("metric-total-transactions", "children"),
        Output("metric-throughput", "children"),
        Output("metric-fraud-count", "children"),
        Output("metric-fraud-rate", "children"),
        Output("metric-quality-score", "children"),
        Output("metric-last-update", "children"),
    ],
    Input("interval-component", "n_intervals")
)
def update_metrics(n):
    """Update key metrics cards."""
    try:
        # Get metrics from collector
        metrics = metrics_collector.get_metrics()
        
        return (
            f"{metrics.transactions_processed:,}",
            f"{metrics.transactions_per_second:.1f} tx/s",
            f"{metrics.fraud_detected:,}",
            f"{metrics.fraud_rate:.2f}% fraud rate",
            f"{metrics.quality_score:.1f}%",
            metrics.last_updated.strftime("%H:%M:%S")
        )
    except Exception as e:
        logger.error(f"Error updating metrics: {e}")
        return "Error", "Error", "Error", "Error", "Error", "Error"


@app.callback(
    Output("graph-transaction-volume", "figure"),
    Input("interval-component", "n_intervals")
)
def update_transaction_volume(n):
    """Update transaction volume graph."""
    try:
        # Query recent transactions from database
        query = """
            SELECT 
                DATE_TRUNC('minute', timestamp) as minute,
                COUNT(*) as transaction_count,
                SUM(total_amount) as revenue
            FROM transactions
            WHERE timestamp > NOW() - INTERVAL '1 hour'
            GROUP BY minute
            ORDER BY minute
        """
        
        df = pd.DataFrame(db_manager.execute_raw_query(query))
        
        if df.empty:
            # Create empty figure
            fig = go.Figure()
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="#1a1a1a",
                plot_bgcolor="#1a1a1a",
                annotations=[{
                    "text": "No data available yet",
                    "xref": "paper",
                    "yref": "paper",
                    "showarrow": False,
                    "font": {"size": 20}
                }]
            )
            return fig
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=df['minute'],
            y=df['transaction_count'],
            mode='lines+markers',
            name='Transactions',
            line=dict(color='#00d9ff', width=2),
            marker=dict(size=6)
        ))
        
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#1a1a1a",
            plot_bgcolor="#1a1a1a",
            xaxis_title="Time",
            yaxis_title="Transaction Count",
            hovermode='x unified',
            showlegend=True
        )
        
        return fig
        
    except Exception as e:
        logger.error(f"Error updating transaction volume: {e}")
        fig = go.Figure()
        fig.update_layout(template="plotly_dark")
        return fig


@app.callback(
    Output("graph-revenue-by-category", "figure"),
    Input("interval-component", "n_intervals")
)
def update_revenue_by_category(n):
    """Update revenue by category pie chart."""
    try:
        query = """
            SELECT 
                category,
                SUM(total_amount) as revenue,
                COUNT(*) as transaction_count
            FROM transactions
            WHERE timestamp > NOW() - INTERVAL '24 hours'
            GROUP BY category
            ORDER BY revenue DESC
            LIMIT 10
        """
        
        df = pd.DataFrame(db_manager.execute_raw_query(query))
        
        if df.empty:
            fig = go.Figure()
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="#1a1a1a",
                plot_bgcolor="#1a1a1a"
            )
            return fig
        
        fig = px.pie(
            df,
            values='revenue',
            names='category',
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#1a1a1a",
            plot_bgcolor="#1a1a1a",
            showlegend=True
        )
        
        return fig
        
    except Exception as e:
        logger.error(f"Error updating revenue by category: {e}")
        fig = go.Figure()
        fig.update_layout(template="plotly_dark")
        return fig


@app.callback(
    Output("graph-fraud-over-time", "figure"),
    Input("interval-component", "n_intervals")
)
def update_fraud_over_time(n):
    """Update fraud detection over time graph."""
    try:
        query = """
            SELECT 
                DATE_TRUNC('minute', timestamp) as minute,
                COUNT(CASE WHEN is_fraud THEN 1 END) as fraud_count,
                COUNT(*) as total_count,
                ROUND(COUNT(CASE WHEN is_fraud THEN 1 END)::numeric / 
                      NULLIF(COUNT(*), 0) * 100, 2) as fraud_rate
            FROM transactions
            WHERE timestamp > NOW() - INTERVAL '1 hour'
            GROUP BY minute
            ORDER BY minute
        """
        
        df = pd.DataFrame(db_manager.execute_raw_query(query))
        
        if df.empty:
            fig = go.Figure()
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="#1a1a1a",
                plot_bgcolor="#1a1a1a"
            )
            return fig
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=df['minute'],
            y=df['fraud_count'],
            name='Fraud Transactions',
            marker_color='#ff4444'
        ))
        
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#1a1a1a",
            plot_bgcolor="#1a1a1a",
            xaxis_title="Time",
            yaxis_title="Fraud Count",
            hovermode='x unified'
        )
        
        return fig
        
    except Exception as e:
        logger.error(f"Error updating fraud over time: {e}")
        fig = go.Figure()
        fig.update_layout(template="plotly_dark")
        return fig


@app.callback(
    Output("graph-customer-segments", "figure"),
    Input("interval-component", "n_intervals")
)
def update_customer_segments(n):
    """Update customer segmentation graph."""
    try:
        query = """
            SELECT 
                customer_segment,
                COUNT(*) as customer_count,
                SUM(total_spent) as total_revenue
            FROM customers
            WHERE customer_segment IS NOT NULL
            GROUP BY customer_segment
            ORDER BY total_revenue DESC
        """
        
        df = pd.DataFrame(db_manager.execute_raw_query(query))
        
        if df.empty:
            # Create sample data for visualization
            df = pd.DataFrame({
                'customer_segment': ['Champions', 'Loyal', 'At Risk', 'New'],
                'customer_count': [100, 250, 150, 300],
                'total_revenue': [50000, 75000, 25000, 30000]
            })
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=df['customer_segment'],
            y=df['customer_count'],
            name='Customer Count',
            marker_color='#00d9ff'
        ))
        
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#1a1a1a",
            plot_bgcolor="#1a1a1a",
            xaxis_title="Segment",
            yaxis_title="Customer Count",
            showlegend=True
        )
        
        return fig
        
    except Exception as e:
        logger.error(f"Error updating customer segments: {e}")
        fig = go.Figure()
        fig.update_layout(template="plotly_dark")
        return fig


@app.callback(
    Output("fraud-alerts-table", "children"),
    Input("interval-component", "n_intervals")
)
def update_fraud_alerts(n):
    """Update fraud alerts table."""
    try:
        query = """
            SELECT 
                transaction_id,
                customer_id,
                total_amount,
                timestamp,
                fraud_reason
            FROM transactions
            WHERE is_fraud = true
            ORDER BY timestamp DESC
            LIMIT 10
        """
        
        df = pd.DataFrame(db_manager.execute_raw_query(query))
        
        if df.empty:
            return html.P("No fraud alerts at this time.", style={"color": "#888"})
        
        # Create table
        table = dbc.Table(
            [
                html.Thead(html.Tr([
                    html.Th("Transaction ID"),
                    html.Th("Customer ID"),
                    html.Th("Amount"),
                    html.Th("Time"),
                    html.Th("Reason")
                ])),
                html.Tbody([
                    html.Tr([
                        html.Td(row['transaction_id'][:8] + "..."),
                        html.Td(row['customer_id']),
                        html.Td(f"${row['total_amount']:.2f}", style={"color": "#ff4444"}),
                        html.Td(str(row['timestamp'])[:19] if row['timestamp'] else "N/A"),
                        html.Td(row['fraud_reason'] if row['fraud_reason'] else "Anomaly detected")
                    ]) for _, row in df.iterrows()
                ])
            ],
            bordered=True,
            dark=True,
            hover=True,
            responsive=True,
            striped=True
        )
        
        return table
        
    except Exception as e:
        logger.error(f"Error updating fraud alerts: {e}")
        return html.P(f"Error loading alerts: {str(e)}", style={"color": "#ff4444"})


def run_dashboard():
    """Run the dashboard server."""
    logger.info(f"Starting dashboard on {config.dashboard.host}:{config.dashboard.port}")
    
    app.run_server(
        host=config.dashboard.host,
        port=config.dashboard.port,
        debug=config.dashboard.debug
    )


if __name__ == "__main__":
    run_dashboard()


