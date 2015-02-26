test:
	py.test --doctest-modules timekpr_service


demo:
	python app.py

deps:
	pip install -r requirements.txt
