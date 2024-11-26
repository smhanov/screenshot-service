#!/usr/bin/env python3
from flask import Flask, request, send_file                                                                                      
import subprocess                                                                                                                
import os                                                                                                                        
import uuid
import threading
import tempfile
import shutil                                                                                                                 
                                                                                                                                
app = Flask(__name__)                                                                                                            
                                                                                                                                
def cleanup_resources(filename, temp_dir, delay=5):                                                                                             
    # Delete the screenshot file and temp directory after a delay                                                                                   
    def cleanup():
        if os.path.exists(filename):
            os.remove(filename)
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
    threading.Timer(delay, cleanup).start()                            
                                                                                                                                
@app.route('/screenshot')                                                                                                        
def take_screenshot():                                                                                                           
    # Get parameters from request                                                                                                
    url = request.args.get('url')                                                                                                
    if not url:                                                                                                                  
        return "URL parameter is required", 400                                                                                  
                                                                                                                                
    width = request.args.get('width', '1280')                                                                                    
    height = request.args.get('height', '900')                                                                                   
    time_budget = request.args.get('time_budget', '1000')
    userAgent= request.args.get('user_agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36')                                                                       
                                                                                                                                
    # Generate unique filename and temp directory for this request                                                                                  
    filename = f"screenshot_{uuid.uuid4()}.png"
    temp_dir = tempfile.mkdtemp(prefix='chrome_')
                                                                                                                                
    try:                                                                                                                         
        # Construct the command                                                                                                  
        cmd = [                                                                                                                  
            'chromium-browser',                                                                                                  
            '--headless',                                                                                                        
            '--disable-gpu',                                                                                                     
            '--no-sandbox',
            f'--user-data-dir={temp_dir}',                                                                                      
            f'--screenshot={filename}',                                                                                          
            f'--window-size={width},{height}',                                                                                   
            f'--virtual-time-budget={time_budget}',
            f'--user-agent="{userAgent}"',                                                                               
            url                                                                                                                  
        ]                                                                                                                        
                                                                                                                                
        # Execute the command                                                                                                    
        subprocess.run(cmd, check=True)                                                                                          
                                                                                                                                
        # Schedule cleanup of resources                                                                                           
        cleanup_resources(filename, temp_dir)                                                                                                   
                                                                                                                                
        # Return the screenshot                                                                                                  
        return send_file(filename, mimetype='image/png')                                                                         
                                                                                                                                
    except subprocess.CalledProcessError as e:                                                                                   
        return f"Failed to take screenshot: {str(e)}", 500                                                                       
    except Exception as e:                                                                                                       
        return f"Error: {str(e)}", 500                                                                                           
                                                                                                                                
if __name__ == '__main__':                                                                                                       
    app.run(host='0.0.0.0', port=5000, threaded=True)   
