from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    operations = [
        migrations.CreateModel(
            name='CreateModel',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('text', models.CharField(max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='DeleteModel',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('text', models.CharField(max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='SaveModel',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('text', models.CharField(max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='UpdateModel',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('text', models.CharField(max_length=100)),
            ],
        ),
    ]
