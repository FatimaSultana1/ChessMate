# Generated by Django 5.1.2 on 2024-10-13 02:45

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chessboard', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Challenge',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('accepted', models.BooleanField(default=False)),
                ('declined', models.BooleanField(default=False)),
                ('challenger', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='challenges_sent', to=settings.AUTH_USER_MODEL)),
                ('opponent', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='challenges_received', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
