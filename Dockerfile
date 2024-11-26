
FROM ubuntu:22.04                                                                                                                

# Install required packages                                                                                                      
RUN apt-get update && apt-get install -y \                                                                                       
  chromium-browser \                                                                                                           
  python3 \                                                                                                                    
  python3-pip \                                                                                                                
  && rm -rf /var/lib/apt/lists/*                                                                                               

# Install Python dependencies                                                                                                    
RUN pip3 install flask                                                                                                           

# Create working directory                                                                                                       
WORKDIR /app                                                                                                                     

# Copy the application                                                                                                           
COPY app.py .                                                                                                                    

# Expose the port                                                                                                                
EXPOSE 5000                                                                                                                      

# Run the server                                                                                                                 
CMD ["python3", "app.py"]    