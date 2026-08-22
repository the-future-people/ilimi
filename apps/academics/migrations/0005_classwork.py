from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('academics', '0004_fix_class_level_order'),
        ('students', '0001_initial'),
        ('tenants', '0001_initial'),
    ]

    operations = [
        migrations.DeleteModel(name='CAComponentScore'),
        migrations.DeleteModel(name='CAComponent'),
        migrations.CreateModel(
            name='Classwork',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('work_type', models.CharField(choices=[('homework', 'Homework'), ('exercise', 'Class Exercise'), ('quiz', 'Quiz'), ('test', 'Class Test'), ('group_work', 'Group Work'), ('project', 'Project')], default='homework', max_length=20)),
                ('name', models.CharField(max_length=100)),
                ('instructions', models.TextField(blank=True)),
                ('attachment', models.FileField(blank=True, null=True, upload_to='classwork/')),
                ('max_score', models.DecimalField(blank=True, decimal_places=2, default=100, max_digits=5, null=True)),
                ('date', models.DateField(help_text='Date the work was set or administered.')),
                ('due_date', models.DateField(blank=True, null=True)),
                ('visible_to_parents', models.BooleanField(default=True)),
                ('allows_digital_submission', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True, null=True)),
                ('branch', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='tenants.branch')),
                ('classroom', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='classwork', to='academics.classroom')),
                ('component_type', models.ForeignKey(blank=True, help_text='Set to count this work toward the CA class score. Null means ungraded.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='components', to='academics.cacomponenttype')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_classwork', to='tenants.schoolmember')),
                ('school', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='classwork', to='tenants.school')),
                ('subject', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='classwork', to='academics.subject')),
                ('term', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='classwork', to='academics.term')),
            ],
            options={
                'ordering': ['-date', 'name'],
                'unique_together': {('classroom', 'subject', 'term', 'name')},
            },
        ),
        migrations.CreateModel(
            name='ClassworkRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('not_done', 'Not Done'), ('done', 'Done'), ('submitted', 'Submitted'), ('graded', 'Graded'), ('excused', 'Excused')], default='not_done', max_length=20)),
                ('score', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('remarks', models.TextField(blank=True)),
                ('submitted_file', models.FileField(blank=True, null=True, upload_to='classwork_submissions/')),
                ('submitted_at', models.DateTimeField(blank=True, null=True)),
                ('marked_at', models.DateTimeField(blank=True, null=True)),
                ('locked', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('classwork', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='records', to='academics.classwork')),
                ('marked_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='marked_classwork_records', to='tenants.schoolmember')),
                ('school', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='classwork_records', to='tenants.school')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='classwork_records', to='students.student')),
            ],
            options={
                'ordering': ['student__last_name', 'student__first_name'],
                'unique_together': {('student', 'classwork')},
            },
        ),
    ]