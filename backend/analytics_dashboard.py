import dash
from dash import dcc, html, Input, Output, callback
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

# Create dummy data for analytics
def generate_dummy_data():
    # Generate chat volume data for the last 30 days
    dates = pd.date_range(start=datetime.now() - timedelta(days=30), end=datetime.now(), freq='D')
    chat_volume = [random.randint(10, 100) for _ in range(len(dates))]
    
    # Generate response time data
    response_times = [random.uniform(0.5, 3.0) for _ in range(len(dates))]
    
    # Generate user satisfaction scores
    satisfaction_scores = [random.uniform(3.5, 5.0) for _ in range(len(dates))]
    
    # Generate topic distribution
    topics = ['Technical Support', 'General Questions', 'Product Info', 'Troubleshooting', 'Feature Requests']
    topic_counts = [random.randint(50, 200) for _ in topics]
    
    # Generate hourly usage pattern
    hours = list(range(24))
    hourly_usage = [random.randint(5, 50) if 9 <= h <= 17 else random.randint(1, 15) for h in hours]
    
    return {
        'dates': dates,
        'chat_volume': chat_volume,
        'response_times': response_times,
        'satisfaction_scores': satisfaction_scores,
        'topics': topics,
        'topic_counts': topic_counts,
        'hours': hours,
        'hourly_usage': hourly_usage
    }

# Initialize Dash app
def create_dash_app():
    app = dash.Dash(__name__, url_base_pathname='/analytics/')
    
    # Generate dummy data
    data = generate_dummy_data()
    
    app.layout = html.Div([
        html.Div([
            html.H1("LangGraph Analytics Dashboard", className="dashboard-title"),
            html.P("Real-time insights into your AI chat application", className="dashboard-subtitle")
        ], className="header-section"),
        
        # KPI Cards
        html.Div([
            html.Div([
                html.H3("2,847", className="kpi-number"),
                html.P("Total Conversations", className="kpi-label"),
                html.Span("↗ +12.5%", className="kpi-change positive")
            ], className="kpi-card"),
            
            html.Div([
                html.H3("1.8s", className="kpi-number"),
                html.P("Avg Response Time", className="kpi-label"),
                html.Span("↘ -0.3s", className="kpi-change positive")
            ], className="kpi-card"),
            
            html.Div([
                html.H3("4.7/5", className="kpi-number"),
                html.P("User Satisfaction", className="kpi-label"),
                html.Span("↗ +0.2", className="kpi-change positive")
            ], className="kpi-card"),
            
            html.Div([
                html.H3("94.2%", className="kpi-number"),
                html.P("Success Rate", className="kpi-label"),
                html.Span("↗ +1.1%", className="kpi-change positive")
            ], className="kpi-card"),
        ], className="kpi-grid"),
        
        # Charts Row 1
        html.Div([
            html.Div([
                dcc.Graph(
                    id='chat-volume-chart',
                    figure={
                        'data': [
                            go.Scatter(
                                x=data['dates'],
                                y=data['chat_volume'],
                                mode='lines+markers',
                                name='Daily Conversations',
                                line=dict(color='#4299e1', width=3),
                                marker=dict(size=6)
                            )
                        ],
                        'layout': go.Layout(
                            title='Daily Chat Volume (Last 30 Days)',
                            xaxis={'title': 'Date'},
                            yaxis={'title': 'Number of Conversations'},
                            hovermode='closest',
                            plot_bgcolor='rgba(0,0,0,0)',
                            paper_bgcolor='rgba(0,0,0,0)',
                        )
                    }
                )
            ], className="chart-container"),
            
            html.Div([
                dcc.Graph(
                    id='response-time-chart',
                    figure={
                        'data': [
                            go.Scatter(
                                x=data['dates'],
                                y=data['response_times'],
                                mode='lines+markers',
                                name='Response Time',
                                line=dict(color='#48bb78', width=3),
                                marker=dict(size=6)
                            )
                        ],
                        'layout': go.Layout(
                            title='Average Response Time Trend',
                            xaxis={'title': 'Date'},
                            yaxis={'title': 'Response Time (seconds)'},
                            hovermode='closest',
                            plot_bgcolor='rgba(0,0,0,0)',
                            paper_bgcolor='rgba(0,0,0,0)',
                        )
                    }
                )
            ], className="chart-container"),
        ], className="charts-row"),
        
        # Charts Row 2
        html.Div([
            html.Div([
                dcc.Graph(
                    id='topic-distribution',
                    figure={
                        'data': [
                            go.Pie(
                                labels=data['topics'],
                                values=data['topic_counts'],
                                hole=0.4,
                                marker_colors=['#4299e1', '#48bb78', '#ed8936', '#9f7aea', '#f56565']
                            )
                        ],
                        'layout': go.Layout(
                            title='Conversation Topics Distribution',
                            plot_bgcolor='rgba(0,0,0,0)',
                            paper_bgcolor='rgba(0,0,0,0)',
                        )
                    }
                )
            ], className="chart-container"),
            
            html.Div([
                dcc.Graph(
                    id='hourly-usage',
                    figure={
                        'data': [
                            go.Bar(
                                x=data['hours'],
                                y=data['hourly_usage'],
                                marker_color='#4299e1',
                                name='Hourly Usage'
                            )
                        ],
                        'layout': go.Layout(
                            title='Usage Pattern by Hour',
                            xaxis={'title': 'Hour of Day'},
                            yaxis={'title': 'Number of Conversations'},
                            plot_bgcolor='rgba(0,0,0,0)',
                            paper_bgcolor='rgba(0,0,0,0)',
                        )
                    }
                )
            ], className="chart-container"),
        ], className="charts-row"),
        
        # Auto-refresh component
        dcc.Interval(
            id='interval-component',
            interval=30*1000,  # Update every 30 seconds
            n_intervals=0
        )
    ])
    
    return app

# Custom CSS for the dashboard
dash_css = """
.dashboard-title {
    color: #2d3748;
    font-size: 2.5rem;
    font-weight: 600;
    margin-bottom: 0.5rem;
}

.dashboard-subtitle {
    color: #718096;
    font-size: 1.1rem;
    margin-bottom: 2rem;
}

.header-section {
    text-align: center;
    padding: 2rem 0;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    margin-bottom: 2rem;
}

.kpi-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 1.5rem;
    margin-bottom: 2rem;
    padding: 0 2rem;
}

.kpi-card {
    background: white;
    padding: 1.5rem;
    border-radius: 12px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    text-align: center;
}

.kpi-number {
    font-size: 2.5rem;
    font-weight: 700;
    color: #2d3748;
    margin-bottom: 0.5rem;
}

.kpi-label {
    color: #718096;
    font-size: 0.9rem;
    margin-bottom: 0.5rem;
}

.kpi-change {
    font-size: 0.8rem;
    font-weight: 600;
}

.kpi-change.positive {
    color: #48bb78;
}

.charts-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 2rem;
    margin-bottom: 2rem;
    padding: 0 2rem;
}

.chart-container {
    background: white;
    border-radius: 12px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    padding: 1rem;
}

@media (max-width: 768px) {
    .charts-row {
        grid-template-columns: 1fr;
    }
    
    .kpi-grid {
        grid-template-columns: 1fr;
    }
}
"""