from flask import Flask, render_template, Response, request, redirect, url_for

app = Flask(__name__)

@app.route('/')
def index():
	return render_template('index.html')

@app.route("/start/", methods=['POST'])
def start_motor():
	#insert motor code
	print("Start pressed")
	forward_message = "Motor is running"
	return render_template('index.html', forward_message=forward_message);

@app.route("/stop/", methods=['POST'])
def stop_motor():
	#insert motor code
	print("Stop pressed")
	forward_message = "Motor is stopped"
	return render_template('index.html', forward_message=forward_message);

if __name__ == '__main__':
	app.run(debug=True, host='0.0.0.0')
