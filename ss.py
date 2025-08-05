import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

from dotenv import load_dotenv
import os
from datetime import datetime
from decimal import Decimal
import mysql.connector
import requests
from bs4 import BeautifulSoup
