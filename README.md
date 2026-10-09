# Flight Management Django Application

This is a Django-based flight management application that allows users to search flights, create bookings, perform online check-in, and receive booking confirmation emails.


## Activate the virtual environment

These commands are required to activate the Python virtual environment before working on the project:

### Navigate to the project directory
```bash
cd C:\Users\User\PycharmProjects\fly_management
```

### Create virtual environment (first time only)
```bash
py -m venv venv
```

### Activate the virtual environment
```bash
venv\Scripts\activate
```


## Environment configuration

Create a `.env` file in the project root directory using the provided `.env.example` file.  
Email credentials are required for sending booking confirmation emails.

```bash
cp .env.example .env
```


## Database setup

```bash
python manage.py makemigrations
python manage.py migrate
```

## Seed flight data

Flight, airline, airport, and route data are imported using a custom Django management command.

```bash
python manage.py seed_openflights --limit-airports 100 --limit-airlines 30 --limit-routes 200
```

## Run the application

```bash
python manage.py runserver
```