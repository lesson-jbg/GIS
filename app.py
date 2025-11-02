import streamlit as st
import requests
import json
from PIL import Image
import io
import base64

# Page configuration
st.set_page_config(
    page_title="GIA Workflow Platform",
    page_icon="🗺️",
    layout="wide"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stButton>button {
        width: 100%;
        background-color: #1f77b4;
        color: white;
        font-weight: bold;
        padding: 0.5rem;
        border-radius: 5px;
    }
    .stButton>button:hover {
        background-color: #145a8c;
    }
    .success-box {
        padding: 1rem;
        border-radius: 5px;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        margin: 1rem 0;
    }
    .error-box {
        padding: 1rem;
        border-radius: 5px;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        margin: 1rem 0;
    }
    </style>
""", unsafe_allow_html=True)

# Header
st.markdown('<p class="main-header">🗺️ GIA Workflow Platform</p>', unsafe_allow_html=True)
st.markdown("---")

# Sidebar for configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    webhook_url = st.text_input(
        "N8N Webhook URL",
        value="http://localhost:5678/webhook-test/recevie-image",
        help="Enter your n8n webhook endpoint URL"
    )
    st.markdown("---")
    st.info("📝 Upload a workflow image to generate SQL queries for GIS analysis")
    
    # Display the prompt that will be sent
    with st.expander("📋 View Analysis Prompt"):
        st.text_area(
            "Prompt sent with image:",
            value="""Analyze this GIS workflow and generate the SQL commands needed to implement it in QGIS.
Instructions:
- Use PostGIS or SpatiaLite syntax.
- Include table creation, spatial joins, and relevant queries.
- Output only the SQL commands, without extra explanation.
If the image contains diagrams or text, use that to infer table structures and operations.""",
            height=200,
            disabled=True
        )

# Main content area
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📤 Upload Workflow Image")
    uploaded_file = st.file_uploader(
        "Choose a workflow image",
        type=["png", "jpg", "jpeg", "bmp", "gif"],
        help="Upload an image of your GIS workflow diagram"
    )
    
    if uploaded_file is not None:
        # Display the uploaded image
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Workflow Image", use_container_width=True)
        
        # Process button
        if st.button("🚀 Process Workflow", type="primary"):
            with st.spinner("Processing workflow... Please wait"):
                try:
                    # Convert image to bytes
                    img_byte_arr = io.BytesIO()
                    image.save(img_byte_arr, format=image.format or 'PNG')
                    img_byte_arr.seek(0)
                    
                    # Prepare the prompt
                    prompt = """Analyze this GIS workflow and generate the SQL commands needed to implement it in QGIS.
Instructions:
- Use PostGIS or SpatiaLite syntax.
- Include table creation, spatial joins, and relevant queries.
- Output only the SQL commands, without extra explanation.
If the image contains diagrams or text, use that to infer table structures and operations."""
                    
                    # Prepare the multipart form data with both image and prompt
                    files = {
                        'file': (uploaded_file.name, img_byte_arr, f'image/{image.format.lower() if image.format else "png"}')
                    }
                    
                    data = {
                        'prompt': prompt
                    }
                    
                    # Send request to n8n webhook with image and prompt
                    response = requests.post(webhook_url, files=files, data=data, timeout=120)
                    
                    if response.status_code == 200:
                        # Parse the response
                        result = response.json()
                        st.session_state['result'] = result
                        st.session_state['success'] = True
                        st.markdown('<div class="success-box">✅ Workflow processed successfully!</div>', unsafe_allow_html=True)
                    else:
                        st.session_state['success'] = False
                        st.markdown(f'<div class="error-box">❌ Error: Server returned status code {response.status_code}</div>', unsafe_allow_html=True)
                        st.error(f"Response: {response.text}")
                        
                except requests.exceptions.RequestException as e:
                    st.session_state['success'] = False
                    st.markdown(f'<div class="error-box">❌ Connection Error: {str(e)}</div>', unsafe_allow_html=True)
                    st.warning("Make sure your n8n instance is running and the webhook URL is correct.")
                except Exception as e:
                    st.session_state['success'] = False
                    st.markdown(f'<div class="error-box">❌ Error: {str(e)}</div>', unsafe_allow_html=True)

with col2:
    st.subheader("📊 Generated SQL Queries")
    
    # Display results if available
    if 'result' in st.session_state and st.session_state.get('success'):
        result = st.session_state['result']
        
        # Extract SQL from the nested structure
        try:
            # Check if result is a list (array format)
            if isinstance(result, list) and len(result) > 0:
                # Get the first item which contains steps
                workflow_data = result[0]
                
                if 'steps' in workflow_data and isinstance(workflow_data['steps'], list):
                    steps = workflow_data['steps']
                    
                    # Collect all SQL queries for download
                    all_sql_queries = []
                    
                    # Display each step
                    for idx, step in enumerate(steps, 1):
                        description = step.get('description', '').strip()
                        sql = step.get('sql', '').strip()
                        
                        # Skip steps with only markdown syntax
                        if description in ['```sql', '```'] and not sql:
                            continue
                        
                        # Clean up description (remove markdown syntax)
                        clean_description = description.replace('```sql', '').replace('```', '').strip()
                        
                        # Display step
                        if clean_description:
                            st.markdown(f"### Step {idx}: {clean_description}")
                        else:
                            st.markdown(f"### Step {idx}")
                        
                        if sql:
                            # Clean SQL (remove trailing markdown syntax)
                            clean_sql = sql.replace('```', '').strip()
                            st.code(clean_sql, language='sql')
                            all_sql_queries.append(f"-- Step {idx}: {clean_description}\n{clean_sql}\n")
                        else:
                            st.info("_No SQL query for this step_")
                        
                        st.markdown("---")
                    
                    # Show download button if there are any SQL queries
                    if all_sql_queries:
                        combined_sql = "\n".join(all_sql_queries)
                        st.download_button(
                            label="📥 Download All SQL Queries",
                            data=combined_sql,
                            file_name="workflow_queries.sql",
                            mime="text/plain",
                            use_container_width=True
                        )
                    else:
                        st.warning("⚠️ No SQL queries found in the workflow")
                else:
                    st.warning("⚠️ No steps found in response")
                    st.json(result)
            
            # Fallback for old format (myField structure)
            elif isinstance(result, dict) and 'myField' in result:
                my_field = result['myField']
                
                if 'description' in my_field and my_field['description']:
                    description = my_field['description']
                    clean_description = description.replace('```sql', '').replace('```', '').strip()
                    st.markdown("**📝 Description:**")
                    st.info(clean_description if clean_description != description else "SQL queries generated from workflow analysis")
                    st.markdown("---")
                
                if 'sql' in my_field and my_field['sql']:
                    sql_code = my_field['sql'].strip()
                    if sql_code:
                        st.markdown("**💾 SQL Query:**")
                        st.code(sql_code, language='sql')
                        st.download_button(
                            label="📥 Download SQL",
                            data=sql_code,
                            file_name="workflow_queries.sql",
                            mime="text/plain"
                        )
            else:
                st.warning("⚠️ Unexpected response format")
                st.info("📄 Raw Response:")
                st.json(result)
                
        except Exception as e:
            st.error(f"Error parsing result: {str(e)}")
            st.info("📄 Raw Response:")
            st.json(result)
    else:
        st.info("👆 Upload a workflow image and click 'Process Workflow' to see the generated SQL queries here.")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; padding: 1rem;'>
        <p>🌍 GIA Platform - Geospatial Intelligence Analysis</p>
        <p style='font-size: 0.8rem;'>Powered by n8n workflows and Streamlit</p>
    </div>
    """,
    unsafe_allow_html=True
)