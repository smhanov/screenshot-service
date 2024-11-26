#!/usr/bin/env python3
from flask import Flask, request, send_file                                                                                      
import subprocess                                                                                                                
import os                                                                                                                        
import uuid                                                                                                                      
import threading                                                                                                                 
                                                                                                                                
app = Flask(__name__)                                                                                                            
                                                                                                                                
def cleanup_file(filename, delay=5):                                                                                             
    # Delete the screenshot file after a delay                                                                                   
    threading.Timer(delay, lambda: os.remove(filename) if os.path.exists(filename) else None).start()                            
                                                                                                                                
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
                                                                                                                                
    # Generate unique filename for this request                                                                                  
    filename = f"screenshot_{uuid.uuid4()}.png"                                                                                  
                                                                                                                                
    try:                                                                                                                         
        # Construct the command                                                                                                  
        cmd = [                                                                                                                  
            'chromium-browser',                                                                                                  
            '--headless',                                                                                                        
            '--disable-gpu',                                                                                                     
            '--no-sandbox',                                                                                                      
            f'--screenshot={filename}',                                                                                          
            f'--window-size={width},{height}',                                                                                   
            f'--virtual-time-budget={time_budget}',
            f'--user-agent="{userAgent}"',                                                                               
            url                                                                                                                  
        ]                                                                                                                        
                                                                                                                                
        # Execute the command                                                                                                    
        subprocess.run(cmd, check=True)                                                                                          
                                                                                                                                
        # Schedule cleanup of the file                                                                                           
        cleanup_file(filename)                                                                                                   
                                                                                                                                
        # Return the screenshot                                                                                                  
        return send_file(filename, mimetype='image/png')                                                                         
                                                                                                                                
    except subprocess.CalledProcessError as e:                                                                                   
        return f"Failed to take screenshot: {str(e)}", 500                                                                       
    except Exception as e:                                                                                                       
        return f"Error: {str(e)}", 500                                                                                           
                                                                                                                                
if __name__ == '__main__':                                                                                                       
    app.run(host='0.0.0.0', port=5000, threaded=True)   