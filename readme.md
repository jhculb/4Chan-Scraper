# 4Chan Scraper
## Author
J. Culbert

## Purpose
Coding challenge over a weekend to implement an application which interfaces with an api for scraping and monitoring purposes.

## Details
* v1: MVP
* v2: Initial steps at dockerisation and hosting on AWS via terraform (incomplete)

## Usage
Run requester.py. (v2 requester.py functional and with the most functionality)

Other functionality includes logging:
* Debug: _Very_ verbose, all actions captured. This includes each polling action. Can be disabled through changing setting in \_\_init\_\_ of the class.

## To do:
* Parametrise polling rate & other default parameters
* Dockerise
* Define desired AWS infrastructure for polling
    * Implement infrastructure in terraform
* Setup.py & requirements fully captured (poetry?)
* CI/CD
    * Jenkins hosted on AWS
    * Code quality: Sonarqube / flake8, pylint, isort, black
    * Pytest unit tests
    * System tests - create stub for 4chan to mock HTTP response

