import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import numpy as np
from tkcalendar import DateEntry
import pickle
import random
from collections import defaultdict
import pandas as pd
import hashlib
import csv
import threading
import time
from functools import lru_cache
import warnings

warnings.filterwarnings('ignore')

# Try to import reportlab, but don't fail if not available
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch

    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("ReportLab not installed. PDF export disabled.")


class Database:
    """Central database management system"""

    def __init__(self):
        self.data_dir = 'fitness_data'
        self.users_file = os.path.join(self.data_dir, 'users.pkl')
        self.workouts_file = os.path.join(self.data_dir, 'workouts.pkl')
        self.nutrition_file = os.path.join(self.data_dir, 'nutrition.pkl')
        self.challenges_file = os.path.join(self.data_dir, 'challenges.pkl')
        self.reports_dir = os.path.join(self.data_dir, 'reports')
        self.backup_dir = os.path.join(self.data_dir, 'backups')

        # Create directories
        for dir_path in [self.data_dir, self.reports_dir, self.backup_dir]:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)

        # Initialize data
        self.data = self.load_all_data()

    def load_all_data(self):
        """Load all data from files"""
        data = {
            'users': {},
            'workouts': [],
            'nutrition': [],
            'challenges': [],
            'achievements': [],
            'user_progress': {}
        }

        # Load users
        if os.path.exists(self.users_file):
            try:
                with open(self.users_file, 'rb') as f:
                    data['users'] = pickle.load(f)
            except:
                data['users'] = {}

        # Load workouts
        if os.path.exists(self.workouts_file):
            try:
                with open(self.workouts_file, 'rb') as f:
                    data['workouts'] = pickle.load(f)
            except:
                data['workouts'] = []

        # Load nutrition
        if os.path.exists(self.nutrition_file):
            try:
                with open(self.nutrition_file, 'rb') as f:
                    data['nutrition'] = pickle.load(f)
            except:
                data['nutrition'] = []

        # Load challenges
        if os.path.exists(self.challenges_file):
            try:
                with open(self.challenges_file, 'rb') as f:
                    data['challenges'] = pickle.load(f)
            except:
                data['challenges'] = self.get_default_challenges()
        else:
            data['challenges'] = self.get_default_challenges()

        return data

    def get_default_challenges(self):
        """Get default challenges"""
        return [
            {
                'id': 1,
                'name': '10K Steps Challenge',
                'description': 'Walk 10,000 steps daily for 30 days',
                'goal': 10000,
                'metric': 'steps',
                'duration': 30,
                'reward': 'Gold Badge',
                'participants': []
            },
            {
                'id': 2,
                'name': 'Hydration Hero',
                'description': 'Drink 8 glasses of water daily',
                'goal': 8,
                'metric': 'water',
                'duration': 30,
                'reward': 'Silver Badge',
                'participants': []
            },
            {
                'id': 3,
                'name': 'Workout Warrior',
                'description': 'Complete 20 workouts in 30 days',
                'goal': 20,
                'metric': 'workouts',
                'duration': 30,
                'reward': 'Platinum Badge',
                'participants': []
            }
        ]

    def save_data(self):
        """Save all data to files"""
        try:
            with open(self.users_file, 'wb') as f:
                pickle.dump(self.data['users'], f)

            with open(self.workouts_file, 'wb') as f:
                pickle.dump(self.data['workouts'], f)

            with open(self.nutrition_file, 'wb') as f:
                pickle.dump(self.data['nutrition'], f)

            with open(self.challenges_file, 'wb') as f:
                pickle.dump(self.data['challenges'], f)

            return True
        except Exception as e:
            print(f"Error saving data: {e}")
            return False

    def create_backup(self):
        """Create backup of all data"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(self.backup_dir, f'backup_{timestamp}.pkl')

        try:
            with open(backup_file, 'wb') as f:
                pickle.dump(self.data, f)
            return backup_file
        except Exception as e:
            print(f"Error creating backup: {e}")
            return None

    def add_user(self, username, password, user_data):
        """Add new user"""
        if username in self.data['users']:
            return False

        # Hash password
        hashed = hashlib.sha256(password.encode()).hexdigest()

        self.data['users'][username] = {
            'password': hashed,
            'created_at': datetime.now().isoformat(),
            'last_login': None,
            'profile': user_data,
            'settings': {
                'notifications': True,
                'dark_mode': True,
                'units': 'metric',
                'weekly_goal': 5
            },
            'stats': {
                'total_workouts': 0,
                'total_calories': 0,
                'total_steps': 0,
                'streak_days': 0,
                'last_workout': None
            },
            'achievements': [],
            'challenges': []
        }

        self.save_data()
        return True

    def verify_user(self, username, password):
        """Verify user credentials"""
        if username not in self.data['users']:
            return False

        hashed = hashlib.sha256(password.encode()).hexdigest()
        if self.data['users'][username]['password'] == hashed:
            self.data['users'][username]['last_login'] = datetime.now().isoformat()
            self.save_data()
            return True

        return False

    def add_workout(self, username, workout_data):
        """Add workout for user"""
        workout = {
            'id': len(self.data['workouts']) + 1,
            'username': username,
            'date': datetime.now().isoformat(),
            **workout_data
        }

        self.data['workouts'].append(workout)

        # Update user stats
        user = self.data['users'][username]
        user['stats']['total_workouts'] += 1
        user['stats']['total_calories'] += workout_data.get('calories', 0)
        user['stats']['last_workout'] = datetime.now().isoformat()

        # Check streak
        self.update_streak(username)

        self.save_data()
        return workout['id']

    def update_streak(self, username):
        """Update user streak"""
        user = self.data['users'][username]
        last_workout = user['stats'].get('last_workout')

        if last_workout:
            last_date = datetime.fromisoformat(last_workout).date()
            today = datetime.now().date()

            if (today - last_date).days <= 1:
                user['stats']['streak_days'] += 1
            else:
                user['stats']['streak_days'] = 1

    def get_user_workouts(self, username, days=30):
        """Get user workouts for last N days"""
        cutoff = datetime.now() - timedelta(days=days)
        workouts = []

        for w in self.data['workouts']:
            if w['username'] == username:
                workout_date = datetime.fromisoformat(w['date'])
                if workout_date >= cutoff:
                    workouts.append(w)

        return workouts

    def generate_report(self, username, report_type='weekly'):
        """Generate fitness report"""
        workouts = self.get_user_workouts(username, 30 if report_type == 'monthly' else 7)

        if not workouts:
            return None

        # Calculate statistics
        stats = {
            'total_workouts': len(workouts),
            'total_calories': sum(w.get('calories', 0) for w in workouts),
            'total_duration': sum(w.get('duration', 0) for w in workouts),
            'avg_calories': sum(w.get('calories', 0) for w in workouts) / len(workouts) if workouts else 0,
            'avg_duration': sum(w.get('duration', 0) for w in workouts) / len(workouts) if workouts else 0,
            'workout_types': defaultdict(int)
        }

        for w in workouts:
            stats['workout_types'][w.get('type', 'Other')] += 1

        return stats


class NotificationManager:
    """Handle notifications and alerts"""

    def __init__(self):
        self.notifications = []
        self.reminders = []

    def add_notification(self, user, title, message, notification_type='info'):
        """Add notification for user"""
        notification = {
            'id': len(self.notifications) + 1,
            'user': user,
            'title': title,
            'message': message,
            'type': notification_type,
            'timestamp': datetime.now().isoformat(),
            'read': False
        }
        self.notifications.append(notification)
        return notification

    def get_user_notifications(self, user, unread_only=False):
        """Get notifications for user"""
        user_notifs = [n for n in self.notifications if n['user'] == user]
        if unread_only:
            user_notifs = [n for n in user_notifs if not n['read']]
        return sorted(user_notifs, key=lambda x: x['timestamp'], reverse=True)

    def mark_as_read(self, notification_id):
        """Mark notification as read"""
        for n in self.notifications:
            if n['id'] == notification_id:
                n['read'] = True
                break

    def add_reminder(self, user, reminder_type, time, message):
        """Add reminder for user"""
        reminder = {
            'id': len(self.reminders) + 1,
            'user': user,
            'type': reminder_type,
            'time': time,
            'message': message,
            'active': True
        }
        self.reminders.append(reminder)
        return reminder


class ReportGenerator:
    """Generate PDF reports"""

    def __init__(self, db):
        self.db = db
        self.reportlab_available = REPORTLAB_AVAILABLE

        if self.reportlab_available:
            self.styles = getSampleStyleSheet()

            # Custom styles
            self.styles.add(ParagraphStyle(
                name='CustomTitle',
                parent=self.styles['Heading1'],
                fontSize=24,
                spaceAfter=30,
                textColor=colors.HexColor('#FF3B30')
            ))

            self.styles.add(ParagraphStyle(
                name='CustomHeading',
                parent=self.styles['Heading2'],
                fontSize=16,
                spaceAfter=12,
                textColor=colors.HexColor('#0A84FF')
            ))

    def generate_weekly_report(self, username, output_path=None):
        """Generate weekly fitness report"""
        if not self.reportlab_available:
            return None

        if not output_path:
            output_path = os.path.join(self.db.reports_dir,
                                       f'weekly_report_{username}_{datetime.now().strftime("%Y%m%d")}.pdf')

        doc = SimpleDocTemplate(output_path, pagesize=A4)
        story = []

        # Title
        title = Paragraph(f"Weekly Fitness Report - {username}", self.styles['CustomTitle'])
        story.append(title)

        # Date
        date = Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y')}", self.styles['Normal'])
        story.append(date)
        story.append(Spacer(1, 20))

        # Get stats
        stats = self.db.generate_report(username, 'weekly')

        if stats:
            # Summary table
            data = [
                ['Metric', 'Value'],
                ['Total Workouts', str(stats['total_workouts'])],
                ['Total Calories', f"{stats['total_calories']} kcal"],
                ['Total Duration', f"{stats['total_duration']} minutes"],
                ['Avg Calories/Workout', f"{stats['avg_calories']:.0f} kcal"],
                ['Avg Duration', f"{stats['avg_duration']:.0f} minutes"]
            ]

            table = Table(data, colWidths=[200, 200])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 14),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))

            story.append(Paragraph('Weekly Summary', self.styles['CustomHeading']))
            story.append(table)
            story.append(Spacer(1, 20))

            # Workout types breakdown
            if stats['workout_types']:
                story.append(Paragraph('Workout Breakdown', self.styles['CustomHeading']))

                type_data = [['Workout Type', 'Count']]
                for w_type, count in stats['workout_types'].items():
                    type_data.append([w_type, str(count)])

                type_table = Table(type_data, colWidths=[200, 200])
                type_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))

                story.append(type_table)

        # Build PDF
        doc.build(story)
        return output_path


class FitnessTrackerGroup8:
    """Fitness Tracker System by Group 8"""

    def __init__(self, root):
        self.root = root
        self.root.title("🏋️ FITNESS TRACKER SYSTEM - GROUP 8")
        self.root.geometry("1600x900")

        # Initialize systems
        self.db = Database()
        self.notification_manager = NotificationManager()
        self.report_generator = ReportGenerator(self.db)

        # Set modern color scheme
        self.colors = {
            'bg': '#000000',
            'card_bg': '#1C1C1E',
            'accent': '#FF3B30',
            'success': '#30D158',
            'warning': '#FFD60A',
            'info': '#0A84FF',
            'text': '#FFFFFF',
            'text_secondary': '#8E8E93',
            'progress_bg': '#2C2C2E',
            'heart_rate': '#FF453A',
            'graph_bg': '#1C1C1E',
            'grid': '#3A3A3C'
        }

        # Current user
        self.current_user = None
        self.current_user_data = None

        # Create main container
        self.main_container = ttk.Frame(self.root)
        self.main_container.pack(fill='both', expand=True)

        # Create GUI
        self.create_styles()
        self.create_header()
        self.create_navigation()
        self.create_main_content()

        # Start background tasks
        self.start_background_tasks()

    def create_styles(self):
        """Create custom styles for modern look"""
        style = ttk.Style()

        # Configure frame styles
        style.configure('Dark.TFrame', background=self.colors['bg'])
        style.configure('Card.TFrame', background=self.colors['card_bg'])
        style.configure('Graph.TFrame', background=self.colors['graph_bg'])

        # Configure label styles
        style.configure('Header.TLabel',
                        background=self.colors['bg'],
                        foreground=self.colors['text'],
                        font=('Helvetica', 24, 'bold'))

        style.configure('SubHeader.TLabel',
                        background=self.colors['bg'],
                        foreground=self.colors['text_secondary'],
                        font=('Helvetica', 14))

        style.configure('Title.TLabel',
                        background=self.colors['card_bg'],
                        foreground=self.colors['text'],
                        font=('Helvetica', 16, 'bold'))

        style.configure('Value.TLabel',
                        background=self.colors['card_bg'],
                        foreground=self.colors['text'],
                        font=('Helvetica', 28, 'bold'))

        style.configure('SmallValue.TLabel',
                        background=self.colors['card_bg'],
                        foreground=self.colors['text'],
                        font=('Helvetica', 20, 'bold'))

        style.configure('Metric.TLabel',
                        background=self.colors['card_bg'],
                        foreground=self.colors['text_secondary'],
                        font=('Helvetica', 12))

        style.configure('Date.TLabel',
                        background=self.colors['bg'],
                        foreground=self.colors['text_secondary'],
                        font=('Helvetica', 14))

        # Configure button styles
        style.configure('Action.TButton',
                        background=self.colors['accent'],
                        foreground=self.colors['text'],
                        font=('Helvetica', 12, 'bold'),
                        padding=10)

        style.configure('Small.TButton',
                        background=self.colors['card_bg'],
                        foreground=self.colors['text'],
                        font=('Helvetica', 10),
                        padding=5)

    def create_header(self):
        """Create header with date, profile and quick actions"""
        header_frame = ttk.Frame(self.main_container, style='Dark.TFrame')
        header_frame.pack(fill='x', padx=30, pady=(20, 10))

        # Left side - Date and title
        left_frame = ttk.Frame(header_frame, style='Dark.TFrame')
        left_frame.pack(side='left')

        date_label = ttk.Label(left_frame,
                               text=f"Last Updated at {datetime.now().strftime('%b %d, %Y at %I:%M %p')}",
                               style='SubHeader.TLabel')
        date_label.pack(anchor='w')

        title_label = ttk.Label(left_frame,
                                text="FITNESS TRACKER SYSTEM - GROUP 8",
                                style='Header.TLabel')
        title_label.pack(anchor='w')

        # Right side - Quick actions and profile
        right_frame = ttk.Frame(header_frame, style='Dark.TFrame')
        right_frame.pack(side='right')

        # Quick action buttons
        actions = ['📊 Log Workout', '💧 Water', '😴 Sleep', '⚖️ Weight', '📄 Report']
        for action in actions:
            btn = tk.Button(right_frame, text=action,
                            bg=self.colors['card_bg'],
                            fg=self.colors['text'],
                            font=('Helvetica', 11),
                            bd=0,
                            padx=15, pady=8,
                            cursor='hand2',
                            command=lambda a=action: self.quick_action(a))
            btn.pack(side='left', padx=5)

            # Hover effect
            btn.bind('<Enter>', lambda e, b=btn: b.configure(bg=self.colors['accent']))
            btn.bind('<Leave>', lambda e, b=btn: b.configure(bg=self.colors['card_bg']))

        # Profile button
        self.profile_btn = tk.Button(right_frame,
                                     text="👤",
                                     font=('Helvetica', 24),
                                     bg=self.colors['bg'],
                                     fg=self.colors['text'],
                                     bd=0,
                                     cursor='hand2',
                                     command=self.show_profile)
        self.profile_btn.pack(side='left', padx=(20, 0))

        # Notification button
        self.notification_btn = tk.Button(right_frame,
                                          text="🔔",
                                          font=('Helvetica', 20),
                                          bg=self.colors['bg'],
                                          fg=self.colors['text'],
                                          bd=0,
                                          cursor='hand2',
                                          command=self.show_notifications)
        self.notification_btn.pack(side='left', padx=(10, 0))

    def create_navigation(self):
        """Create navigation tabs"""
        nav_frame = ttk.Frame(self.main_container, style='Dark.TFrame')
        nav_frame.pack(fill='x', padx=30, pady=(10, 20))

        # Navigation buttons
        nav_items = [
            ('📊 DASHBOARD', 0),
            ('📈 PROGRESS', 1),
            ('💪 WORKOUTS', 2),
            ('📋 PLANS', 3),
            ('🏆 CHALLENGES', 4),
            ('📚 LIBRARY', 5),
            ('👥 SOCIAL', 6),
            ('⚙️ SETTINGS', 7)
        ]

        self.nav_buttons = []
        for text, index in nav_items:
            btn = tk.Button(nav_frame, text=text,
                            bg=self.colors['bg'],
                            fg=self.colors['text_secondary'],
                            font=('Helvetica', 13, 'bold'),
                            bd=0,
                            padx=20, pady=10,
                            cursor='hand2',
                            command=lambda i=index: self.show_tab(i))
            btn.pack(side='left', padx=2)
            self.nav_buttons.append(btn)

        # Current tab indicator
        self.current_tab = 0
        self.update_navigation()

    def update_navigation(self):
        """Update navigation button colors"""
        for i, btn in enumerate(self.nav_buttons):
            if i == self.current_tab:
                btn.configure(fg=self.colors['accent'],
                              bg=self.colors['card_bg'])
            else:
                btn.configure(fg=self.colors['text_secondary'],
                              bg=self.colors['bg'])

    def show_tab(self, index):
        """Show selected tab"""
        self.current_tab = index
        self.update_navigation()

        # Hide all content frames
        for frame in self.content_frames:
            frame.pack_forget()

        # Show selected frame
        self.content_frames[index].pack(fill='both', expand=True)

        # Update tab content
        if index == 0:
            self.update_dashboard()
        elif index == 1:
            self.update_progress_tab()
        elif index == 2:
            self.update_workouts_tab()
        elif index == 3:
            self.update_plans_tab()
        elif index == 4:
            self.update_challenges_tab()
        elif index == 6:
            self.update_social_tab()
        elif index == 7:
            self.update_settings_tab()

    def create_main_content(self):
        """Create main content area with tabs"""
        self.content_frames = []

        # Create frames for each tab
        self.content_frames.append(self.create_dashboard_tab())
        self.content_frames.append(self.create_progress_tab())
        self.content_frames.append(self.create_workouts_tab())
        self.content_frames.append(self.create_plans_tab())
        self.content_frames.append(self.create_challenges_tab())
        self.content_frames.append(self.create_library_tab())
        self.content_frames.append(self.create_social_tab())
        self.content_frames.append(self.create_settings_tab())

        # Show dashboard by default
        self.content_frames[0].pack(fill='both', expand=True)

    def create_dashboard_tab(self):
        """Create enhanced dashboard tab"""
        frame = ttk.Frame(self.main_container, style='Dark.TFrame')

        # Create main dashboard layout
        main_dashboard = ttk.Frame(frame, style='Dark.TFrame')
        main_dashboard.pack(fill='both', expand=True, padx=30, pady=10)

        # Left column - Schedule and Activity Rings
        left_col = ttk.Frame(main_dashboard, style='Dark.TFrame')
        left_col.pack(side='left', fill='y', padx=(0, 15))

        self.create_enhanced_schedule(left_col)
        self.create_activity_rings_card(left_col)
        self.create_notifications_card(left_col)

        # Middle column - Goals and Stats
        middle_col = ttk.Frame(main_dashboard, style='Dark.TFrame')
        middle_col.pack(side='left', fill='both', expand=True, padx=7)

        self.create_goals_card(middle_col)
        self.create_detailed_stats(middle_col)

        # Right column - Health Metrics
        right_col = ttk.Frame(main_dashboard, style='Dark.TFrame')
        right_col.pack(side='left', fill='both', expand=True, padx=(15, 0))

        self.create_heart_rate_card(right_col)
        self.create_health_metrics(right_col)
        self.create_recent_activity(right_col)

        return frame

    def create_enhanced_schedule(self, parent):
        """Create enhanced schedule with workout indicators"""
        card = ttk.Frame(parent, style='Card.TFrame')
        card.pack(fill='x', pady=(0, 15))

        # Header with add button
        header = ttk.Frame(card, style='Card.TFrame')
        header.pack(fill='x', padx=15, pady=(15, 10))

        ttk.Label(header, text="📅 SCHEDULE", style='Title.TLabel').pack(side='left')

        add_btn = tk.Button(header, text="+ Add Workout",
                            bg=self.colors['success'],
                            fg=self.colors['text'],
                            font=('Helvetica', 10),
                            bd=0,
                            padx=10, pady=5,
                            cursor='hand2',
                            command=self.add_to_schedule)
        add_btn.pack(side='right')

        # Days grid
        days_frame = ttk.Frame(card, style='Card.TFrame')
        days_frame.pack(padx=15, pady=(0, 15))

        days = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']
        today = datetime.now().weekday()

        # Get user workouts for the week if logged in
        weekly_workouts = {}
        if self.current_user:
            workouts = self.db.get_user_workouts(self.current_user, 7)
            for w in workouts:
                w_date = datetime.fromisoformat(w['date']).date()
                weekly_workouts[w_date.strftime('%A')[:3].upper()] = w

        for i, day in enumerate(days):
            day_card = tk.Frame(days_frame, bg=self.colors['progress_bg'],
                                width=80, height=100)
            day_card.grid(row=0, column=i, padx=5, pady=5)
            day_card.grid_propagate(False)

            # Highlight today
            if i == today:
                day_card.configure(bg=self.colors['accent'])

            # Day name
            day_label = tk.Label(day_card, text=day,
                                 bg=day_card['bg'],
                                 fg=self.colors['text'] if i == today else self.colors['text_secondary'],
                                 font=('Helvetica', 10))
            day_label.pack(pady=(10, 5))

            # Date
            current_date = datetime.now() + timedelta(days=i - today)
            date_label = tk.Label(day_card, text=current_date.strftime('%d'),
                                  bg=day_card['bg'],
                                  fg=self.colors['text'],
                                  font=('Helvetica', 20, 'bold'))
            date_label.pack()

            # Workout indicator
            if day in weekly_workouts:
                indicator = tk.Label(day_card, text="●",
                                     bg=day_card['bg'],
                                     fg=self.colors['success'],
                                     font=('Helvetica', 15))
                indicator.pack()

    def create_activity_rings_card(self, parent):
        """Create enhanced activity rings with real data"""
        card = ttk.Frame(parent, style='Card.TFrame')
        card.pack(fill='x', pady=(0, 15))

        ttk.Label(card, text="🔴 ACTIVITY RINGS", style='Title.TLabel').pack(anchor='w', padx=15, pady=(15, 10))

        rings_frame = ttk.Frame(card, style='Card.TFrame')
        rings_frame.pack(pady=10)

        # Get real data if user logged in
        if self.current_user:
            workouts = self.db.get_user_workouts(self.current_user, 1)
            calories_burned = sum(w.get('calories', 0) for w in workouts)
            exercise_minutes = sum(w.get('duration', 0) for w in workouts)
            stand_hours = random.randint(6, 10)  # This would come from device data

            activities = [
                ('MOVE', calories_burned, 600, self.colors['accent']),
                ('EXERCISE', exercise_minutes, 30, self.colors['success']),
                ('STAND', stand_hours, 12, self.colors['info'])
            ]
        else:
            activities = [
                ('MOVE', 307, 600, self.colors['accent']),
                ('EXERCISE', 24, 30, self.colors['success']),
                ('STAND', 7, 12, self.colors['info'])
            ]

        for i, (label, current, goal, color) in enumerate(activities):
            self.create_enhanced_ring(rings_frame, label, current, goal, color, i // 2, i % 2)

    def create_enhanced_ring(self, parent, label, current, goal, color, row, col):
        """Create enhanced circular progress ring"""
        frame = ttk.Frame(parent, style='Card.TFrame')
        frame.grid(row=row, column=col, padx=25, pady=10)

        # Canvas for ring
        canvas_size = 120
        canvas = tk.Canvas(frame, width=canvas_size, height=canvas_size,
                           bg=self.colors['card_bg'], highlightthickness=0)
        canvas.pack()

        # Calculate progress
        progress = min(current / goal, 1.0)
        angle = 360 * progress

        # Draw background ring
        canvas.create_arc(15, 15, 105, 105, start=0, extent=360,
                          outline=self.colors['progress_bg'], width=10, style='arc')

        # Draw progress ring
        if progress > 0:
            canvas.create_arc(15, 15, 105, 105, start=90, extent=-angle,
                              outline=color, width=10, style='arc')

        # Center text
        canvas.create_text(60, 50, text=f"{current}",
                           fill=self.colors['text'],
                           font=('Helvetica', 16, 'bold'))
        canvas.create_text(60, 75, text=label,
                           fill=self.colors['text_secondary'],
                           font=('Helvetica', 8))

        # Goal text
        goal_label = tk.Label(frame, text=f"Goal: {goal}",
                              bg=self.colors['card_bg'],
                              fg=self.colors['text_secondary'],
                              font=('Helvetica', 9))
        goal_label.pack()

    def create_notifications_card(self, parent):
        """Create notifications card"""
        card = ttk.Frame(parent, style='Card.TFrame')
        card.pack(fill='x')

        header = ttk.Frame(card, style='Card.TFrame')
        header.pack(fill='x', padx=15, pady=(15, 10))

        ttk.Label(header, text="🔔 NOTIFICATIONS", style='Title.TLabel').pack(side='left')

        if self.current_user:
            unread = len(
                [n for n in self.notification_manager.get_user_notifications(self.current_user) if not n['read']])
            if unread > 0:
                ttk.Label(header, text=f"{unread} new",
                          foreground=self.colors['success'],
                          font=('Helvetica', 10, 'bold')).pack(side='right')

        # Show recent notifications
        notif_frame = ttk.Frame(card, style='Card.TFrame')
        notif_frame.pack(fill='x', padx=15, pady=10)

        if self.current_user:
            notifications = self.notification_manager.get_user_notifications(self.current_user)[:3]
            if notifications:
                for notif in notifications:
                    self.create_notification_item(notif_frame, notif)
            else:
                ttk.Label(notif_frame, text="No new notifications",
                          style='Metric.TLabel').pack(pady=20)
        else:
            ttk.Label(notif_frame, text="Login to see notifications",
                      style='Metric.TLabel').pack(pady=20)

    def create_notification_item(self, parent, notification):
        """Create notification item"""
        frame = tk.Frame(parent, bg=self.colors['progress_bg'],
                         height=40)
        frame.pack(fill='x', pady=2)
        frame.pack_propagate(False)

        # Notification type indicator
        colors = {
            'info': self.colors['info'],
            'success': self.colors['success'],
            'warning': self.colors['warning'],
            'reminder': self.colors['accent']
        }

        indicator = tk.Label(frame, text="●",
                             bg=self.colors['progress_bg'],
                             fg=colors.get(notification['type'], self.colors['info']),
                             font=('Helvetica', 10))
        indicator.pack(side='left', padx=10)

        # Message
        msg_label = tk.Label(frame, text=notification['message'][:30] + "...",
                             bg=self.colors['progress_bg'],
                             fg=self.colors['text'],
                             font=('Helvetica', 10))
        msg_label.pack(side='left', padx=5)

    def create_goals_card(self, parent):
        """Create enhanced goals card with real data"""
        card = ttk.Frame(parent, style='Card.TFrame')
        card.pack(fill='x', pady=(0, 15))

        # Header
        header = ttk.Frame(card, style='Card.TFrame')
        header.pack(fill='x', padx=15, pady=(15, 10))

        ttk.Label(header, text="🎯 WEEKLY GOALS", style='Title.TLabel').pack(side='left')

        # Goals based on user data
        if self.current_user:
            workouts = self.db.get_user_workouts(self.current_user, 7)
            steps = sum(w.get('steps', 0) for w in workouts)
            calories = sum(w.get('calories', 0) for w in workouts)
            distance = sum(w.get('distance', 0) for w in workouts)

            goals = [
                ('Steps', f"{steps:,}", '10,000', min(int(steps / 10000 * 100), 100)),
                ('Calories', f"{calories}", '2,200', min(int(calories / 2200 * 100), 100)),
                ('Distance', f"{distance:.1f}", '8 km', min(int(distance / 8 * 100), 100)),
                ('Water', '4', '8 cups', 50)
            ]
        else:
            goals = [
                ('Steps', '8,500', '10,000', 85),
                ('Calories', '1,850', '2,200', 84),
                ('Distance', '5.2', '8 km', 65),
                ('Water', '4', '8 cups', 50)
            ]

        goals_frame = ttk.Frame(card, style='Card.TFrame')
        goals_frame.pack(fill='x', padx=15, pady=10)

        for goal, current, target, progress in goals:
            self.create_goal_item(goals_frame, goal, current, target, progress)

    def create_goal_item(self, parent, goal, current, target, progress):
        """Create individual goal item"""
        frame = ttk.Frame(parent, style='Card.TFrame')
        frame.pack(fill='x', pady=5)

        # Goal info
        info_frame = ttk.Frame(frame, style='Card.TFrame')
        info_frame.pack(fill='x')

        ttk.Label(info_frame, text=goal, style='Metric.TLabel').pack(side='left')
        ttk.Label(info_frame, text=f"{current} / {target}",
                  style='SmallValue.TLabel', font=('Helvetica', 14)).pack(side='right')

        # Progress bar
        progress_frame = ttk.Frame(frame, style='Card.TFrame')
        progress_frame.pack(fill='x', pady=(5, 0))

        canvas = tk.Canvas(progress_frame, height=6, bg=self.colors['progress_bg'],
                           highlightthickness=0)
        canvas.pack(fill='x', side='left', expand=True)

        bar_width = int(progress * 3)  # Assuming canvas width 300
        canvas.create_rectangle(0, 0, bar_width, 6,
                                fill=self.colors['success'], outline='')

        ttk.Label(progress_frame, text=f"{progress}%",
                  style='Metric.TLabel', font=('Helvetica', 9)).pack(side='right', padx=(5, 0))

    def create_detailed_stats(self, parent):
        """Create detailed statistics grid"""
        card = ttk.Frame(parent, style='Card.TFrame')
        card.pack(fill='both', expand=True)

        ttk.Label(card, text="📊 DETAILED STATS", style='Title.TLabel').pack(anchor='w', padx=15, pady=(15, 10))

        stats_frame = ttk.Frame(card, style='Card.TFrame')
        stats_frame.pack(fill='both', expand=True, padx=15, pady=10)

        # Get real stats if user logged in
        if self.current_user:
            user = self.db.data['users'][self.current_user]
            stats = [
                ('🔥 Active Calories', f"{user['stats']['total_calories']} kcal", f"+{user['stats']['streak_days']}%"),
                ('💪 Workouts', str(user['stats']['total_workouts']), f"{user['stats']['streak_days']} day streak"),
                ('🏃 Last Workout', 'Today' if user['stats'].get('last_workout') else 'Never', 'Active'),
                ('🎯 Weekly Goal', f"{user['stats']['total_workouts']}/5",
                 f"{min(user['stats']['total_workouts'] * 20, 100)}%")
            ]
        else:
            stats = [
                ('🔥 Active Calories', '2,847 kcal', '+12%'),
                ('💪 Workouts', '12', '3 day streak'),
                ('🏃 Last Workout', 'Today', 'Active'),
                ('🎯 Weekly Goal', '3/5', '60%')
            ]

        for i, (stat, value, change) in enumerate(stats):
            self.create_stat_item(stats_frame, stat, value, change, i % 2)

        # Mini graph
        self.create_mini_graph(card)

    def create_stat_item(self, parent, stat, value, change, col):
        """Create individual stat item"""
        frame = tk.Frame(parent, bg=self.colors['progress_bg'],
                         width=200, height=80)
        frame.grid(row=0, column=col, padx=5, pady=5)
        frame.grid_propagate(False)

        tk.Label(frame, text=stat,
                 bg=self.colors['progress_bg'],
                 fg=self.colors['text_secondary'],
                 font=('Helvetica', 10)).pack(anchor='w', padx=10, pady=(15, 5))

        tk.Label(frame, text=value,
                 bg=self.colors['progress_bg'],
                 fg=self.colors['text'],
                 font=('Helvetica', 16, 'bold')).pack(side='left', padx=10)

        change_color = self.colors['success'] if '+' in change else self.colors['text_secondary']
        tk.Label(frame, text=change,
                 bg=self.colors['progress_bg'],
                 fg=change_color,
                 font=('Helvetica', 10)).pack(side='left', padx=5)

    def create_mini_graph(self, parent):
        """Create mini trend graph"""
        frame = ttk.Frame(parent, style='Card.TFrame')
        frame.pack(fill='x', padx=15, pady=15)

        # Get real data if user logged in
        if self.current_user:
            workouts = self.db.get_user_workouts(self.current_user, 7)
            days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            calories_by_day = [0] * 7

            for w in workouts:
                w_date = datetime.fromisoformat(w['date'])
                day_index = w_date.weekday()
                calories_by_day[day_index] += w.get('calories', 0)

            y = calories_by_day
        else:
            y = [65, 72, 68, 85, 78, 92, 88]

        # Create mini matplotlib figure
        fig = Figure(figsize=(5, 1.5), dpi=70)
        fig.patch.set_facecolor(self.colors['card_bg'])
        ax = fig.add_subplot(111)
        ax.set_facecolor(self.colors['card_bg'])

        x = range(7)
        ax.plot(x, y, color=self.colors['success'], linewidth=2, marker='o', markersize=4)
        ax.fill_between(x, y, alpha=0.1, color=self.colors['success'])

        # Style
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_color(self.colors['text_secondary'])
        ax.spines['left'].set_color(self.colors['text_secondary'])
        ax.tick_params(colors=self.colors['text_secondary'], labelsize=8)
        ax.set_xticks(x)
        ax.set_xticklabels(['M', 'T', 'W', 'T', 'F', 'S', 'S'])

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, frame)
        canvas.draw()
        canvas.get_tk_widget().pack()

    def create_heart_rate_card(self, parent):
        """Create enhanced heart rate card"""
        card = ttk.Frame(parent, style='Card.TFrame')
        card.pack(fill='x', pady=(0, 15))

        header = ttk.Frame(card, style='Card.TFrame')
        header.pack(fill='x', padx=15, pady=(15, 10))

        ttk.Label(header, text="❤️ HEART RATE", style='Title.TLabel').pack(side='left')

        # Heart rate display
        hr_frame = ttk.Frame(card, style='Card.TFrame')
        hr_frame.pack(pady=10)

        # Large heart icon
        heart_label = tk.Label(hr_frame, text="❤️",
                               font=('Helvetica', 60),
                               bg=self.colors['card_bg'],
                               fg=self.colors['heart_rate'])
        heart_label.pack(side='left', padx=20)

        # Value
        value_frame = ttk.Frame(hr_frame, style='Card.TFrame')
        value_frame.pack(side='left', padx=20)

        ttk.Label(value_frame, text="77", style='Value.TLabel',
                  font=('Helvetica', 48, 'bold')).pack(anchor='w')
        ttk.Label(value_frame, text="bpm • Resting", style='Metric.TLabel').pack(anchor='w')

        # Heart rate graph
        self.create_heart_rate_graph(card)

    def create_heart_rate_graph(self, parent):
        """Create heart rate trend graph"""
        frame = ttk.Frame(parent, style='Card.TFrame')
        frame.pack(fill='x', padx=15, pady=10)

        fig = Figure(figsize=(4, 1.5), dpi=70)
        fig.patch.set_facecolor(self.colors['card_bg'])
        ax = fig.add_subplot(111)
        ax.set_facecolor(self.colors['card_bg'])

        # Sample heart rate data
        x = range(24)
        y = [68, 65, 62, 60, 58, 59, 62, 68, 75, 82, 88, 92,
             95, 90, 85, 82, 78, 75, 72, 70, 68, 67, 66, 65]

        ax.plot(x, y, color=self.colors['heart_rate'], linewidth=1.5)
        ax.fill_between(x, 50, y, alpha=0.2, color=self.colors['heart_rate'])

        # Style
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_color(self.colors['text_secondary'])
        ax.spines['left'].set_color(self.colors['text_secondary'])
        ax.tick_params(colors=self.colors['text_secondary'], labelsize=6)
        ax.set_ylim(50, 100)
        ax.set_xticks([0, 6, 12, 18, 23])
        ax.set_xticklabels(['12 AM', '6 AM', '12 PM', '6 PM', '11 PM'])

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, frame)
        canvas.draw()
        canvas.get_tk_widget().pack()

    def create_health_metrics(self, parent):
        """Create health metrics cards"""
        card = ttk.Frame(parent, style='Card.TFrame')
        card.pack(fill='x', pady=(0, 15))

        ttk.Label(card, text="📈 HEALTH METRICS", style='Title.TLabel').pack(anchor='w', padx=15, pady=(15, 10))

        metrics_frame = ttk.Frame(card, style='Card.TFrame')
        metrics_frame.pack(fill='x', padx=15, pady=10)

        metrics = [
            ('💧 Water', '44.2 oz', '65%', self.colors['info']),
            ('😴 Sleep', '7h 23m', '92%', self.colors['success']),
            ('⚖️ Weight', '72.5 kg', '-2.3 kg', self.colors['warning']),
            ('🧠 HRV', '45 ms', 'Good', self.colors['accent'])
        ]

        for metric, value, sub, color in metrics:
            self.create_metric_item(metrics_frame, metric, value, sub, color)

    def create_metric_item(self, parent, metric, value, sub, color):
        """Create individual metric item"""
        frame = tk.Frame(parent, bg=self.colors['progress_bg'],
                         height=60)
        frame.pack(fill='x', pady=3)
        frame.pack_propagate(False)

        tk.Label(frame, text=metric,
                 bg=self.colors['progress_bg'],
                 fg=self.colors['text_secondary'],
                 font=('Helvetica', 10)).pack(side='left', padx=10)

        tk.Label(frame, text=value,
                 bg=self.colors['progress_bg'],
                 fg=self.colors['text'],
                 font=('Helvetica', 14, 'bold')).pack(side='right', padx=10)

        tk.Label(frame, text=sub,
                 bg=self.colors['progress_bg'],
                 fg=color,
                 font=('Helvetica', 9)).pack(side='right', padx=5)

    def create_recent_activity(self, parent):
        """Create recent activity feed"""
        card = ttk.Frame(parent, style='Card.TFrame')
        card.pack(fill='both', expand=True)

        header = ttk.Frame(card, style='Card.TFrame')
        header.pack(fill='x', padx=15, pady=(15, 10))

        ttk.Label(header, text="🕒 RECENT ACTIVITY", style='Title.TLabel').pack(side='left')

        view_btn = tk.Button(header, text="View All",
                             bg=self.colors['card_bg'],
                             fg=self.colors['info'],
                             font=('Helvetica', 10),
                             bd=0,
                             cursor='hand2',
                             command=self.show_all_activity)
        view_btn.pack(side='right')

        # Activity list
        activity_frame = ttk.Frame(card, style='Card.TFrame')
        activity_frame.pack(fill='both', expand=True, padx=15, pady=10)

        # Get real activities if user logged in
        if self.current_user:
            workouts = self.db.get_user_workouts(self.current_user, 7)[:5]
            activities = []
            for w in workouts:
                w_date = datetime.fromisoformat(w['date'])
                time_ago = self.get_time_ago(w_date)
                activities.append((
                    f"🏃 {w.get('type', 'Workout')}",
                    f"{w.get('duration', 0)} min • {w.get('calories', 0)} kcal",
                    time_ago,
                    self.colors['success']
                ))
        else:
            activities = [
                ('🏃 Running', '5.2 km • 307 kcal', '2h ago', self.colors['accent']),
                ('💪 Strength', '45 min • Upper body', '5h ago', self.colors['success']),
                ('🧘 Yoga', '30 min • Flexibility', 'Yesterday', self.colors['info']),
                ('🏊 Swimming', '1.2 km • 150 kcal', 'Yesterday', self.colors['warning']),
                ('🚶 Walking', '8,542 steps', 'Yesterday', self.colors['text_secondary'])
            ]

        for activity, details, time, color in activities:
            self.create_activity_item(activity_frame, activity, details, time, color)

    def get_time_ago(self, dt):
        """Get human readable time difference"""
        diff = datetime.now() - dt
        if diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds // 3600 > 0:
            return f"{diff.seconds // 3600}h ago"
        elif diff.seconds // 60 > 0:
            return f"{diff.seconds // 60}m ago"
        else:
            return "Just now"

    def create_activity_item(self, parent, activity, details, time, color):
        """Create individual activity item"""
        frame = tk.Frame(parent, bg=self.colors['progress_bg'],
                         height=50)
        frame.pack(fill='x', pady=2)
        frame.pack_propagate(False)

        # Activity icon/color
        icon = tk.Label(frame, text="●",
                        bg=self.colors['progress_bg'],
                        fg=color,
                        font=('Helvetica', 15))
        icon.pack(side='left', padx=(10, 5))

        # Activity details
        text_frame = tk.Frame(frame, bg=self.colors['progress_bg'])
        text_frame.pack(side='left', fill='both', expand=True)

        tk.Label(text_frame, text=activity,
                 bg=self.colors['progress_bg'],
                 fg=self.colors['text'],
                 font=('Helvetica', 11, 'bold')).pack(anchor='w')

        tk.Label(text_frame, text=details,
                 bg=self.colors['progress_bg'],
                 fg=self.colors['text_secondary'],
                 font=('Helvetica', 8)).pack(anchor='w')

        # Time
        tk.Label(frame, text=time,
                 bg=self.colors['progress_bg'],
                 fg=self.colors['text_secondary'],
                 font=('Helvetica', 8)).pack(side='right', padx=10)

    def create_progress_tab(self):
        """Create enhanced progress tracking tab"""
        frame = ttk.Frame(self.main_container, style='Dark.TFrame')

        # Controls
        controls = ttk.Frame(frame, style='Dark.TFrame')
        controls.pack(fill='x', padx=30, pady=20)

        # Time period selector
        period_frame = ttk.Frame(controls, style='Dark.TFrame')
        period_frame.pack(side='left')

        periods = ['Week', 'Month', '3 Months', '6 Months', 'Year']
        self.period_var = tk.StringVar(value='Month')
        self.period_buttons = []

        for period in periods:
            btn = tk.Button(period_frame, text=period,
                            bg=self.colors['card_bg'] if period == 'Month' else self.colors['bg'],
                            fg=self.colors['text'],
                            font=('Helvetica', 11),
                            bd=0,
                            padx=15, pady=8,
                            cursor='hand2',
                            command=lambda p=period: self.change_period(p))
            btn.pack(side='left', padx=2)
            self.period_buttons.append(btn)

        # Metric selector
        metric_frame = ttk.Frame(controls, style='Dark.TFrame')
        metric_frame.pack(side='right')

        ttk.Label(metric_frame, text="View:", style='Metric.TLabel').pack(side='left', padx=10)

        metrics = ['All', 'Weight', 'Calories', 'Heart Rate', 'Steps', 'Duration']
        self.metric_var = tk.StringVar(value='All')
        metric_combo = ttk.Combobox(metric_frame, textvariable=self.metric_var,
                                    values=metrics, width=15, state='readonly')
        metric_combo.pack(side='left', padx=5)
        metric_combo.bind('<<ComboboxSelected>>', self.update_progress_graphs)

        # Export button
        export_btn = tk.Button(metric_frame, text="📊 Export Report",
                               bg=self.colors['success'],
                               fg=self.colors['text'],
                               font=('Helvetica', 11, 'bold'),
                               bd=0,
                               padx=15, pady=8,
                               cursor='hand2',
                               command=self.export_progress_report)
        export_btn.pack(side='left', padx=10)

        # Graphs container with scrollbar
        canvas_container = ttk.Frame(frame, style='Dark.TFrame')
        canvas_container.pack(fill='both', expand=True, padx=30, pady=10)

        # Create canvas and scrollbar
        self.progress_canvas = tk.Canvas(canvas_container, bg=self.colors['bg'],
                                         highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_container, orient='vertical',
                                  command=self.progress_canvas.yview)
        self.progress_graphs = ttk.Frame(self.progress_canvas, style='Dark.TFrame')

        self.progress_graphs.bind('<Configure>',
                                  lambda e: self.progress_canvas.configure(
                                      scrollregion=self.progress_canvas.bbox('all')))

        self.progress_canvas.create_window((0, 0), window=self.progress_graphs, anchor='nw')
        self.progress_canvas.configure(yscrollcommand=scrollbar.set)

        self.progress_canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        return frame

    def change_period(self, period):
        """Change progress graph period"""
        self.period_var.set(period)
        # Update button colors
        for btn in self.period_buttons:
            if btn['text'] == period:
                btn.configure(bg=self.colors['card_bg'])
            else:
                btn.configure(bg=self.colors['bg'])
        self.update_progress_graphs()

    def update_progress_tab(self):
        """Update progress tab with graphs"""
        self.update_progress_graphs()

    def update_progress_graphs(self, event=None):
        """Update all progress graphs based on selected metric"""
        # Clear previous graphs
        for widget in self.progress_graphs.winfo_children():
            widget.destroy()

        metric = self.metric_var.get()
        period = self.period_var.get()

        if metric == 'All':
            # Create multiple graphs in grid
            graphs_frame = ttk.Frame(self.progress_graphs, style='Dark.TFrame')
            graphs_frame.pack(fill='both', expand=True)

            # Weight graph
            weight_frame = ttk.Frame(graphs_frame, style='Card.TFrame')
            weight_frame.grid(row=0, column=0, padx=5, pady=5, sticky='nsew')
            self.create_weight_graph(weight_frame, period)

            # Calories graph
            calories_frame = ttk.Frame(graphs_frame, style='Card.TFrame')
            calories_frame.grid(row=0, column=1, padx=5, pady=5, sticky='nsew')
            self.create_calories_graph(calories_frame, period)

            # Heart rate graph
            hr_frame = ttk.Frame(graphs_frame, style='Card.TFrame')
            hr_frame.grid(row=1, column=0, padx=5, pady=5, sticky='nsew')
            self.create_heart_rate_graph_tab(hr_frame, period)

            # Steps graph
            steps_frame = ttk.Frame(graphs_frame, style='Card.TFrame')
            steps_frame.grid(row=1, column=1, padx=5, pady=5, sticky='nsew')
            self.create_steps_graph(steps_frame, period)

            # Configure grid weights
            graphs_frame.grid_columnconfigure(0, weight=1)
            graphs_frame.grid_columnconfigure(1, weight=1)
            graphs_frame.grid_rowconfigure(0, weight=1)
            graphs_frame.grid_rowconfigure(1, weight=1)

        else:
            # Create single large graph
            self.create_large_graph(self.progress_graphs, metric, period)

    def get_date_range(self, period):
        """Get date range for period"""
        end_date = datetime.now()
        if period == 'Week':
            start_date = end_date - timedelta(days=7)
        elif period == 'Month':
            start_date = end_date - timedelta(days=30)
        elif period == '3 Months':
            start_date = end_date - timedelta(days=90)
        elif period == '6 Months':
            start_date = end_date - timedelta(days=180)
        else:  # Year
            start_date = end_date - timedelta(days=365)
        return start_date, end_date

    def create_weight_graph(self, parent, period):
        """Create weight progress graph"""
        ttk.Label(parent, text="Weight Progress", style='Title.TLabel').pack(anchor='w', padx=10, pady=10)

        fig = Figure(figsize=(5, 3), dpi=80)
        fig.patch.set_facecolor(self.colors['card_bg'])
        ax = fig.add_subplot(111)
        ax.set_facecolor(self.colors['card_bg'])

        # Get date range
        start_date, end_date = self.get_date_range(period)

        # Generate sample data (replace with real data)
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        if self.current_user:
            # Would get real weight data from database
            base_weight = 75
            weights = base_weight + np.cumsum(np.random.randn(len(dates)) * 0.05)
        else:
            weights = 75 + np.cumsum(np.random.randn(len(dates)) * 0.1)

        ax.plot(dates, weights, color=self.colors['success'], linewidth=2)
        ax.scatter(dates[::5], weights[::5], color=self.colors['success'], s=30, zorder=5)

        # Style
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_color(self.colors['text_secondary'])
        ax.spines['left'].set_color(self.colors['text_secondary'])
        ax.tick_params(colors=self.colors['text_secondary'], labelsize=8)
        ax.set_ylabel('Weight (kg)', color=self.colors['text_secondary'])
        ax.grid(True, alpha=0.2, color=self.colors['text_secondary'])

        fig.autofmt_xdate()
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)

    def create_calories_graph(self, parent, period):
        """Create calories burned graph"""
        ttk.Label(parent, text="Calories Burned", style='Title.TLabel').pack(anchor='w', padx=10, pady=10)

        fig = Figure(figsize=(5, 3), dpi=80)
        fig.patch.set_facecolor(self.colors['card_bg'])
        ax = fig.add_subplot(111)
        ax.set_facecolor(self.colors['card_bg'])

        # Get date range
        start_date, end_date = self.get_date_range(period)

        # Generate data
        if period == 'Week':
            days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            if self.current_user:
                workouts = self.db.get_user_workouts(self.current_user, 7)
                calories = [0] * 7
                for w in workouts:
                    w_date = datetime.fromisoformat(w['date'])
                    day_index = w_date.weekday()
                    calories[day_index] += w.get('calories', 0)
            else:
                calories = [450, 380, 520, 490, 610, 720, 580]

            bars = ax.bar(days, calories, color=self.colors['accent'], alpha=0.8)

            # Add value labels
            for bar, val in zip(bars, calories):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width() / 2., height,
                        f'{val}', ha='center', va='bottom', color=self.colors['text'],
                        fontsize=8)
        else:
            # For longer periods, use line plot
            dates = pd.date_range(start=start_date, end=end_date, freq='W' if period == 'Month' else 'M')
            if self.current_user:
                calories = [random.randint(2000, 3500) for _ in range(len(dates))]
            else:
                calories = [random.randint(2000, 3500) for _ in range(len(dates))]

            ax.plot(dates, calories, color=self.colors['accent'], linewidth=2, marker='o')
            ax.fill_between(dates, min(calories), calories, alpha=0.2, color=self.colors['accent'])

        # Style
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_color(self.colors['text_secondary'])
        ax.spines['left'].set_color(self.colors['text_secondary'])
        ax.tick_params(colors=self.colors['text_secondary'], labelsize=8)
        ax.set_ylabel('Calories', color=self.colors['text_secondary'])
        ax.grid(True, alpha=0.2, axis='y', color=self.colors['text_secondary'])

        fig.autofmt_xdate()
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)

    def create_heart_rate_graph_tab(self, parent, period):
        """Create heart rate graph for progress tab"""
        ttk.Label(parent, text="Heart Rate Trends", style='Title.TLabel').pack(anchor='w', padx=10, pady=10)

        fig = Figure(figsize=(5, 3), dpi=80)
        fig.patch.set_facecolor(self.colors['card_bg'])
        ax = fig.add_subplot(111)
        ax.set_facecolor(self.colors['card_bg'])

        # Get date range
        start_date, end_date = self.get_date_range(period)

        if period == 'Week':
            # Daily average
            days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            hr_data = [68, 72, 70, 75, 73, 78, 71]
            bars = ax.bar(days, hr_data, color=self.colors['heart_rate'], alpha=0.8)

            for bar, val in zip(bars, hr_data):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width() / 2., height,
                        f'{val}', ha='center', va='bottom', color=self.colors['text'],
                        fontsize=8)
        else:
            # Hourly pattern
            hours = range(24)
            hr = [68, 65, 62, 60, 58, 59, 62, 68, 75, 82, 88, 92,
                  95, 90, 85, 82, 78, 75, 72, 70, 68, 67, 66, 65]

            ax.plot(hours, hr, color=self.colors['heart_rate'], linewidth=2)
            ax.fill_between(hours, 50, hr, alpha=0.3, color=self.colors['heart_rate'])
            ax.set_xlabel('Hour', color=self.colors['text_secondary'])

        # Style
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_color(self.colors['text_secondary'])
        ax.spines['left'].set_color(self.colors['text_secondary'])
        ax.tick_params(colors=self.colors['text_secondary'], labelsize=8)
        ax.set_ylabel('BPM', color=self.colors['text_secondary'])
        ax.grid(True, alpha=0.2, color=self.colors['text_secondary'])
        ax.set_ylim(50, 100)

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)

    def create_steps_graph(self, parent, period):
        """Create steps graph"""
        ttk.Label(parent, text="Daily Steps", style='Title.TLabel').pack(anchor='w', padx=10, pady=10)

        fig = Figure(figsize=(5, 3), dpi=80)
        fig.patch.set_facecolor(self.colors['card_bg'])
        ax = fig.add_subplot(111)
        ax.set_facecolor(self.colors['card_bg'])

        # Get date range
        start_date, end_date = self.get_date_range(period)

        # Generate data
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        steps = [random.randint(5000, 12000) for _ in range(len(dates))]

        ax.plot(dates, steps, color=self.colors['info'], linewidth=2)
        ax.fill_between(dates, 5000, steps, alpha=0.2, color=self.colors['info'])

        # Goal line
        ax.axhline(y=10000, color=self.colors['warning'], linestyle='--', alpha=0.5, label='Goal')

        # Style
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_color(self.colors['text_secondary'])
        ax.spines['left'].set_color(self.colors['text_secondary'])
        ax.tick_params(colors=self.colors['text_secondary'], labelsize=8)
        ax.set_ylabel('Steps', color=self.colors['text_secondary'])
        ax.grid(True, alpha=0.2, color=self.colors['text_secondary'])
        ax.legend()

        fig.autofmt_xdate()
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)

    def create_large_graph(self, parent, metric, period):
        """Create large single graph"""
        frame = ttk.Frame(parent, style='Card.TFrame')
        frame.pack(fill='both', expand=True, padx=5, pady=5)

        ttk.Label(frame, text=f"{metric} Analysis - {period}", style='Title.TLabel').pack(anchor='w', padx=10, pady=10)

        fig = Figure(figsize=(12, 6), dpi=80)
        fig.patch.set_facecolor(self.colors['card_bg'])
        ax = fig.add_subplot(111)
        ax.set_facecolor(self.colors['card_bg'])

        # Get date range
        start_date, end_date = self.get_date_range(period)
        dates = pd.date_range(start=start_date, end=end_date, freq='D')

        # Generate data based on metric
        if metric == 'Weight':
            data = 75 + np.cumsum(np.random.randn(len(dates)) * 0.1)
            color = self.colors['success']
            ylabel = 'Weight (kg)'
        elif metric == 'Calories':
            data = 500 + np.random.randn(len(dates)) * 100
            color = self.colors['accent']
            ylabel = 'Calories'
        elif metric == 'Heart Rate':
            data = 70 + np.random.randn(len(dates)) * 5
            color = self.colors['heart_rate']
            ylabel = 'BPM'
        elif metric == 'Steps':
            data = 8000 + np.random.randn(len(dates)) * 2000
            color = self.colors['info']
            ylabel = 'Steps'
        else:  # Duration
            data = 30 + np.random.randn(len(dates)) * 10
            color = self.colors['warning']
            ylabel = 'Minutes'

        # Plot
        ax.plot(dates, data, color=color, linewidth=2, label='Actual')

        # Add trend line
        z = np.polyfit(range(len(data)), data, 1)
        trend = np.poly1d(z)
        ax.plot(dates, trend(range(len(data))), '--', color=self.colors['warning'],
                linewidth=1.5, label='Trend')

        # Add moving average
        window = min(7, len(data) // 3)
        if window > 1:
            ma = pd.Series(data).rolling(window=window).mean()
            ax.plot(dates, ma, color=self.colors['info'], linewidth=1.5,
                    label=f'{window}-day Average')

        # Style
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_color(self.colors['text_secondary'])
        ax.spines['left'].set_color(self.colors['text_secondary'])
        ax.tick_params(colors=self.colors['text_secondary'], labelsize=9)
        ax.set_ylabel(ylabel, color=self.colors['text_secondary'], fontsize=11)
        ax.set_xlabel('Date', color=self.colors['text_secondary'], fontsize=11)
        ax.grid(True, alpha=0.2, color=self.colors['text_secondary'])
        ax.legend()

        fig.autofmt_xdate()
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)

        # Add toolbar
        toolbar_frame = ttk.Frame(frame, style='Card.TFrame')
        toolbar_frame.pack(fill='x')
        toolbar = NavigationToolbar2Tk(canvas, toolbar_frame)
        toolbar.update()

    def create_workouts_tab(self):
        """Create workouts tab"""
        frame = ttk.Frame(self.main_container, style='Dark.TFrame')

        # Header with add button
        header = ttk.Frame(frame, style='Dark.TFrame')
        header.pack(fill='x', padx=30, pady=20)

        ttk.Label(header, text="💪 WORKOUT HISTORY", style='Header.TLabel').pack(side='left')

        add_btn = tk.Button(header, text="+ Log Workout",
                            bg=self.colors['success'],
                            fg=self.colors['text'],
                            font=('Helvetica', 12, 'bold'),
                            bd=0,
                            padx=20, pady=10,
                            cursor='hand2',
                            command=lambda: self.quick_action('📊 Log Workout'))
        add_btn.pack(side='right')

        # Filter controls
        filter_frame = ttk.Frame(frame, style='Dark.TFrame')
        filter_frame.pack(fill='x', padx=30, pady=(0, 20))

        ttk.Label(filter_frame, text="Filter by:", style='Metric.TLabel').pack(side='left', padx=(0, 10))

        # Workout type filter
        self.workout_type_var = tk.StringVar(value='All')
        types = ['All', 'Running', 'Cycling', 'Swimming', 'Strength', 'Yoga', 'Walking']
        type_combo = ttk.Combobox(filter_frame, textvariable=self.workout_type_var,
                                  values=types, width=15, state='readonly')
        type_combo.pack(side='left', padx=5)
        type_combo.bind('<<ComboboxSelected>>', self.filter_workouts)

        # Date range filter
        ttk.Label(filter_frame, text="From:", style='Metric.TLabel').pack(side='left', padx=(20, 5))
        self.from_date = DateEntry(filter_frame, width=12, background='darkblue',
                                   foreground='white', borderwidth=2)
        self.from_date.pack(side='left', padx=5)

        ttk.Label(filter_frame, text="To:", style='Metric.TLabel').pack(side='left', padx=(10, 5))
        self.to_date = DateEntry(filter_frame, width=12, background='darkblue',
                                 foreground='white', borderwidth=2)
        self.to_date.pack(side='left', padx=5)

        # Workouts list with scrollbar
        list_container = ttk.Frame(frame, style='Dark.TFrame')
        list_container.pack(fill='both', expand=True, padx=30, pady=10)

        # Create Treeview
        columns = ('Date', 'Type', 'Duration', 'Calories', 'Distance', 'Notes')
        self.workouts_tree = ttk.Treeview(list_container, columns=columns, show='headings', height=20)

        # Define headings
        for col in columns:
            self.workouts_tree.heading(col, text=col)
            self.workouts_tree.column(col, width=100)

        # Add scrollbars
        vsb = ttk.Scrollbar(list_container, orient='vertical', command=self.workouts_tree.yview)
        hsb = ttk.Scrollbar(list_container, orient='horizontal', command=self.workouts_tree.xview)
        self.workouts_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # Grid layout
        self.workouts_tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')

        list_container.grid_rowconfigure(0, weight=1)
        list_container.grid_columnconfigure(0, weight=1)

        # Bind double-click
        self.workouts_tree.bind('<Double-1>', self.view_workout_details)

        return frame

    def update_workouts_tab(self):
        """Update workouts tab with user data"""
        if not self.current_user:
            return

        # Clear existing items
        for item in self.workouts_tree.get_children():
            self.workouts_tree.delete(item)

        # Get workouts
        workouts = self.db.get_user_workouts(self.current_user, 365)  # Get all workouts from last year

        # Insert workouts
        for w in sorted(workouts, key=lambda x: x['date'], reverse=True):
            date = datetime.fromisoformat(w['date']).strftime('%Y-%m-%d %H:%M')
            self.workouts_tree.insert('', 'end', values=(
                date,
                w.get('type', 'Unknown'),
                f"{w.get('duration', 0)} min",
                f"{w.get('calories', 0)} kcal",
                f"{w.get('distance', 0)} km",
                w.get('notes', '')[:30]
            ))

    def filter_workouts(self, event=None):
        """Filter workouts based on criteria"""
        if not self.current_user:
            return

        workout_type = self.workout_type_var.get()
        from_date = self.from_date.get_date()
        to_date = self.to_date.get_date()

        # Clear existing items
        for item in self.workouts_tree.get_children():
            self.workouts_tree.delete(item)

        # Get and filter workouts
        workouts = self.db.get_user_workouts(self.current_user, 365)

        for w in sorted(workouts, key=lambda x: x['date'], reverse=True):
            w_date = datetime.fromisoformat(w['date']).date()

            # Apply filters
            if w_date < from_date or w_date > to_date:
                continue

            if workout_type != 'All' and w.get('type') != workout_type:
                continue

            date_str = w_date.strftime('%Y-%m-%d %H:%M')
            self.workouts_tree.insert('', 'end', values=(
                date_str,
                w.get('type', 'Unknown'),
                f"{w.get('duration', 0)} min",
                f"{w.get('calories', 0)} kcal",
                f"{w.get('distance', 0)} km",
                w.get('notes', '')[:30]
            ))

    def view_workout_details(self, event):
        """View workout details on double-click"""
        selection = self.workouts_tree.selection()
        if not selection:
            return

        item = self.workouts_tree.item(selection[0])
        values = item['values']

        # Create detail dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Workout Details")
        dialog.geometry("400x500")
        dialog.configure(bg=self.colors['bg'])

        main_frame = ttk.Frame(dialog, style='Card.TFrame')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        # Workout details
        details = [
            ('Date', values[0]),
            ('Type', values[1]),
            ('Duration', values[2]),
            ('Calories', values[3]),
            ('Distance', values[4]),
            ('Notes', values[5])
        ]

        for label, value in details:
            frame = ttk.Frame(main_frame, style='Card.TFrame')
            frame.pack(fill='x', pady=5)

            ttk.Label(frame, text=label, style='Metric.TLabel').pack(side='left')
            ttk.Label(frame, text=value, style='SmallValue.TLabel',
                      font=('Helvetica', 12)).pack(side='right')

        # Edit and Delete buttons
        button_frame = ttk.Frame(main_frame, style='Card.TFrame')
        button_frame.pack(fill='x', pady=20)

        tk.Button(button_frame, text="Edit",
                  bg=self.colors['info'],
                  fg=self.colors['text'],
                  font=('Helvetica', 12),
                  bd=0,
                  padx=20, pady=10,
                  cursor='hand2',
                  command=lambda: self.edit_workout(values)).pack(side='left', padx=5)

        tk.Button(button_frame, text="Delete",
                  bg=self.colors['accent'],
                  fg=self.colors['text'],
                  font=('Helvetica', 12),
                  bd=0,
                  padx=20, pady=10,
                  cursor='hand2',
                  command=lambda: self.delete_workout(values)).pack(side='right', padx=5)

    def create_plans_tab(self):
        """Create workout plans tab"""
        frame = ttk.Frame(self.main_container, style='Dark.TFrame')

        # Header
        header = ttk.Frame(frame, style='Dark.TFrame')
        header.pack(fill='x', padx=30, pady=20)

        ttk.Label(header, text="📋 WORKOUT PLANS", style='Header.TLabel').pack(side='left')

        # Create plan button
        create_btn = tk.Button(header, text="+ Create Plan",
                               bg=self.colors['success'],
                               fg=self.colors['text'],
                               font=('Helvetica', 12, 'bold'),
                               bd=0,
                               padx=20, pady=10,
                               cursor='hand2',
                               command=self.create_workout_plan)
        create_btn.pack(side='right')

        # Plans grid
        plans_frame = ttk.Frame(frame, style='Dark.TFrame')
        plans_frame.pack(fill='both', expand=True, padx=30, pady=10)

        # Sample plans
        plans = [
            {
                'name': 'Beginner 5K Runner',
                'description': '8-week program to run your first 5K',
                'duration': '8 weeks',
                'level': 'Beginner',
                'workouts': 24,
                'color': self.colors['success']
            },
            {
                'name': 'Strength Builder',
                'description': '12-week strength training program',
                'duration': '12 weeks',
                'level': 'Intermediate',
                'workouts': 36,
                'color': self.colors['accent']
            },
            {
                'name': 'Weight Loss Challenge',
                'description': 'Intensive 4-week weight loss program',
                'duration': '4 weeks',
                'level': 'All Levels',
                'workouts': 20,
                'color': self.colors['warning']
            },
            {
                'name': 'Yoga for Flexibility',
                'description': 'Daily yoga practice for better flexibility',
                'duration': 'Ongoing',
                'level': 'Beginner',
                'workouts': 30,
                'color': self.colors['info']
            }
        ]

        for i, plan in enumerate(plans):
            self.create_plan_card(plans_frame, plan, i)

        return frame

    def create_plan_card(self, parent, plan, index):
        """Create plan card"""
        card = tk.Frame(parent, bg=self.colors['card_bg'],
                        width=350, height=200)
        card.grid(row=index // 2, column=index % 2, padx=10, pady=10)
        card.grid_propagate(False)

        # Plan name
        tk.Label(card, text=plan['name'],
                 bg=self.colors['card_bg'],
                 fg=self.colors['text'],
                 font=('Helvetica', 16, 'bold')).pack(anchor='w', padx=15, pady=(15, 5))

        # Description
        tk.Label(card, text=plan['description'],
                 bg=self.colors['card_bg'],
                 fg=self.colors['text_secondary'],
                 font=('Helvetica', 11)).pack(anchor='w', padx=15)

        # Details frame
        details_frame = tk.Frame(card, bg=self.colors['card_bg'])
        details_frame.pack(fill='x', padx=15, pady=10)

        # Duration
        tk.Label(details_frame, text=f"⏱️ {plan['duration']}",
                 bg=self.colors['card_bg'],
                 fg=self.colors['text_secondary'],
                 font=('Helvetica', 10)).pack(side='left', padx=5)

        # Level
        tk.Label(details_frame, text=f"📊 {plan['level']}",
                 bg=self.colors['card_bg'],
                 fg=self.colors['text_secondary'],
                 font=('Helvetica', 10)).pack(side='left', padx=5)

        # Workouts
        tk.Label(details_frame, text=f"💪 {plan['workouts']} workouts",
                 bg=self.colors['card_bg'],
                 fg=self.colors['text_secondary'],
                 font=('Helvetica', 10)).pack(side='right', padx=5)

        # Start button
        tk.Button(card, text="Start Plan",
                  bg=plan['color'],
                  fg=self.colors['text'],
                  font=('Helvetica', 12, 'bold'),
                  bd=0,
                  padx=30, pady=8,
                  cursor='hand2',
                  command=lambda: self.start_plan(plan)).pack(pady=15)

    def create_workout_plan(self):
        """Create custom workout plan"""
        if not self.current_user:
            messagebox.showinfo("Login Required", "Please login to create a plan")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Create Workout Plan")
        dialog.geometry("500x600")
        dialog.configure(bg=self.colors['bg'])

        main_frame = ttk.Frame(dialog, style='Card.TFrame')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        ttk.Label(main_frame, text="Create Your Plan",
                  style='Value.TLabel', font=('Helvetica', 20)).pack(pady=20)

        # Plan name
        ttk.Label(main_frame, text="Plan Name", style='Metric.TLabel').pack(pady=(10, 5))
        name_entry = ttk.Entry(main_frame, width=40, font=('Helvetica', 12))
        name_entry.pack(pady=5)

        # Goal selection
        ttk.Label(main_frame, text="Primary Goal", style='Metric.TLabel').pack(pady=(10, 5))
        goal_var = tk.StringVar()
        goals = ['Weight Loss', 'Muscle Gain', 'Endurance', 'Flexibility', 'General Fitness']
        goal_combo = ttk.Combobox(main_frame, textvariable=goal_var, values=goals,
                                  width=38, state='readonly')
        goal_combo.pack(pady=5)

        # Duration
        ttk.Label(main_frame, text="Duration (weeks)", style='Metric.TLabel').pack(pady=(10, 5))
        duration_spin = tk.Spinbox(main_frame, from_=1, to=52, width=38,
                                   font=('Helvetica', 12))
        duration_spin.pack(pady=5)

        # Days per week
        ttk.Label(main_frame, text="Workouts per Week", style='Metric.TLabel').pack(pady=(10, 5))
        days_spin = tk.Spinbox(main_frame, from_=1, to=7, width=38,
                               font=('Helvetica', 12))
        days_spin.pack(pady=5)

        # Experience level
        ttk.Label(main_frame, text="Experience Level", style='Metric.TLabel').pack(pady=(10, 5))
        level_var = tk.StringVar()
        levels = ['Beginner', 'Intermediate', 'Advanced']
        level_combo = ttk.Combobox(main_frame, textvariable=level_var, values=levels,
                                   width=38, state='readonly')
        level_combo.pack(pady=5)

        # Create button
        def save_plan():
            plan_data = {
                'name': name_entry.get(),
                'goal': goal_var.get(),
                'duration': duration_spin.get(),
                'days_per_week': days_spin.get(),
                'level': level_var.get(),
                'created_at': datetime.now().isoformat(),
                'user': self.current_user
            }

            if not all(plan_data.values()):
                messagebox.showerror("Error", "Please fill all fields")
                return

            # Save plan logic here
            messagebox.showinfo("Success", "Plan created successfully!")
            dialog.destroy()

        tk.Button(main_frame, text="Create Plan",
                  bg=self.colors['success'],
                  fg=self.colors['text'],
                  font=('Helvetica', 14, 'bold'),
                  bd=0,
                  padx=40, pady=12,
                  cursor='hand2',
                  command=save_plan).pack(pady=30)

    def start_plan(self, plan):
        """Start a workout plan"""
        if not self.current_user:
            messagebox.showinfo("Login Required", "Please login to start a plan")
            return

        response = messagebox.askyesno("Start Plan",
                                       f"Do you want to start the '{plan['name']}' plan?")
        if response:
            messagebox.showinfo("Success", "Plan started! Check your dashboard for today's workout.")

    def create_challenges_tab(self):
        """Create challenges tab"""
        frame = ttk.Frame(self.main_container, style='Dark.TFrame')

        # Header
        header = ttk.Frame(frame, style='Dark.TFrame')
        header.pack(fill='x', padx=30, pady=20)

        ttk.Label(header, text="🏆 ACTIVE CHALLENGES", style='Header.TLabel').pack(side='left')

        # My challenges button
        my_btn = tk.Button(header, text="My Challenges",
                           bg=self.colors['info'],
                           fg=self.colors['text'],
                           font=('Helvetica', 12),
                           bd=0,
                           padx=20, pady=10,
                           cursor='hand2',
                           command=self.show_my_challenges)
        my_btn.pack(side='right', padx=5)

        # Create challenge button
        create_btn = tk.Button(header, text="+ Create Challenge",
                               bg=self.colors['success'],
                               fg=self.colors['text'],
                               font=('Helvetica', 12, 'bold'),
                               bd=0,
                               padx=20, pady=10,
                               cursor='hand2',
                               command=self.create_challenge)
        create_btn.pack(side='right', padx=5)

        # Challenges grid with scrollbar
        canvas_container = ttk.Frame(frame, style='Dark.TFrame')
        canvas_container.pack(fill='both', expand=True, padx=30, pady=10)

        canvas = tk.Canvas(canvas_container, bg=self.colors['bg'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_container, orient='vertical', command=canvas.yview)
        self.challenges_frame = ttk.Frame(canvas, style='Dark.TFrame')

        self.challenges_frame.bind('<Configure>',
                                   lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=self.challenges_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # Load challenges
        self.load_challenges()

        return frame

    def load_challenges(self):
        """Load challenges from database"""
        # Clear existing
        for widget in self.challenges_frame.winfo_children():
            widget.destroy()

        challenges = self.db.data['challenges']

        for i, challenge in enumerate(challenges):
            self.create_challenge_card(self.challenges_frame, challenge, i)

    def create_challenge_card(self, parent, challenge, index):
        """Create challenge card"""
        card = tk.Frame(parent, bg=self.colors['card_bg'],
                        width=350, height=250)
        card.grid(row=index // 2, column=index % 2, padx=10, pady=10)
        card.grid_propagate(False)

        # Challenge name
        tk.Label(card, text=challenge['name'],
                 bg=self.colors['card_bg'],
                 fg=self.colors['text'],
                 font=('Helvetica', 16, 'bold')).pack(anchor='w', padx=15, pady=(15, 5))

        # Description
        tk.Label(card, text=challenge['description'],
                 bg=self.colors['card_bg'],
                 fg=self.colors['text_secondary'],
                 font=('Helvetica', 11),
                 wraplength=320).pack(anchor='w', padx=15)

        # Progress circle if user participating
        if self.current_user and challenge['id'] in [c['id'] for c in
                                                     self.db.data['users'][self.current_user].get('challenges', [])]:
            # Show progress
            canvas = tk.Canvas(card, width=60, height=60,
                               bg=self.colors['card_bg'], highlightthickness=0)
            canvas.pack(pady=10)

            # Draw progress circle (example: 65%)
            canvas.create_arc(10, 10, 50, 50, start=0, extent=360,
                              outline=self.colors['progress_bg'], width=3, style='arc')
            canvas.create_arc(10, 10, 50, 50, start=90, extent=234,
                              outline=self.colors['success'], width=3, style='arc')
            canvas.create_text(30, 30, text="65%",
                               fill=self.colors['text'],
                               font=('Helvetica', 10, 'bold'))
        else:
            # Join button
            tk.Button(card, text="Join Challenge",
                      bg=self.colors['success'],
                      fg=self.colors['text'],
                      font=('Helvetica', 12, 'bold'),
                      bd=0,
                      padx=30, pady=8,
                      cursor='hand2',
                      command=lambda: self.join_challenge(challenge)).pack(pady=15)

        # Challenge details
        details_frame = tk.Frame(card, bg=self.colors['card_bg'])
        details_frame.pack(fill='x', padx=15, pady=5)

        tk.Label(details_frame, text=f"🎯 Goal: {challenge['goal']} {challenge['metric']}",
                 bg=self.colors['card_bg'],
                 fg=self.colors['text_secondary'],
                 font=('Helvetica', 10)).pack(anchor='w')

        tk.Label(details_frame, text=f"⏱️ Duration: {challenge['duration']} days",
                 bg=self.colors['card_bg'],
                 fg=self.colors['text_secondary'],
                 font=('Helvetica', 10)).pack(anchor='w')

        tk.Label(details_frame, text=f"🏅 Reward: {challenge['reward']}",
                 bg=self.colors['card_bg'],
                 fg=self.colors['warning'],
                 font=('Helvetica', 10, 'bold')).pack(anchor='w')

        # Participants
        participants = len(challenge.get('participants', []))
        tk.Label(details_frame, text=f"👥 {participants} participants",
                 bg=self.colors['card_bg'],
                 fg=self.colors['text_secondary'],
                 font=('Helvetica', 9)).pack(anchor='w', pady=(5, 0))

    def join_challenge(self, challenge):
        """Join a challenge"""
        if not self.current_user:
            messagebox.showinfo("Login Required", "Please login to join challenges")
            return

        response = messagebox.askyesno("Join Challenge",
                                       f"Do you want to join the '{challenge['name']}' challenge?")
        if response:
            # Add user to challenge participants
            if 'participants' not in challenge:
                challenge['participants'] = []

            if self.current_user not in challenge['participants']:
                challenge['participants'].append(self.current_user)

                # Add to user's challenges
                if 'challenges' not in self.db.data['users'][self.current_user]:
                    self.db.data['users'][self.current_user]['challenges'] = []

                self.db.data['users'][self.current_user]['challenges'].append({
                    'id': challenge['id'],
                    'joined_at': datetime.now().isoformat(),
                    'progress': 0
                })

                self.db.save_data()

                # Add notification
                self.notification_manager.add_notification(
                    self.current_user,
                    "Challenge Joined!",
                    f"You've joined the {challenge['name']} challenge. Good luck!",
                    'success'
                )

                messagebox.showinfo("Success", "You've joined the challenge!")

    def show_my_challenges(self):
        """Show user's challenges"""
        if not self.current_user:
            messagebox.showinfo("Login Required", "Please login to view your challenges")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("My Challenges")
        dialog.geometry("500x400")
        dialog.configure(bg=self.colors['bg'])

        main_frame = ttk.Frame(dialog, style='Card.TFrame')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        ttk.Label(main_frame, text="Your Active Challenges",
                  style='Value.TLabel', font=('Helvetica', 18)).pack(pady=20)

        user_challenges = self.db.data['users'][self.current_user].get('challenges', [])

        if not user_challenges:
            ttk.Label(main_frame, text="You haven't joined any challenges yet",
                      style='Metric.TLabel').pack(pady=30)
        else:
            for challenge in user_challenges:
                # Find challenge details
                challenge_data = next((c for c in self.db.data['challenges']
                                       if c['id'] == challenge['id']), None)
                if challenge_data:
                    frame = tk.Frame(main_frame, bg=self.colors['progress_bg'],
                                     height=60)
                    frame.pack(fill='x', pady=5)
                    frame.pack_propagate(False)

                    tk.Label(frame, text=challenge_data['name'],
                             bg=self.colors['progress_bg'],
                             fg=self.colors['text'],
                             font=('Helvetica', 12, 'bold')).pack(side='left', padx=10)

                    tk.Label(frame, text=f"Progress: {challenge['progress']}%",
                             bg=self.colors['progress_bg'],
                             fg=self.colors['success'],
                             font=('Helvetica', 11)).pack(side='right', padx=10)

        # Close button
        tk.Button(main_frame, text="Close",
                  bg=self.colors['accent'],
                  fg=self.colors['text'],
                  font=('Helvetica', 12),
                  bd=0,
                  padx=30, pady=10,
                  cursor='hand2',
                  command=dialog.destroy).pack(pady=20)

    def create_challenge(self):
        """Create a new challenge"""
        if not self.current_user:
            messagebox.showinfo("Login Required", "Please login to create a challenge")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Create Challenge")
        dialog.geometry("500x600")
        dialog.configure(bg=self.colors['bg'])

        main_frame = ttk.Frame(dialog, style='Card.TFrame')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        ttk.Label(main_frame, text="Create New Challenge",
                  style='Value.TLabel', font=('Helvetica', 20)).pack(pady=20)

        # Challenge name
        ttk.Label(main_frame, text="Challenge Name", style='Metric.TLabel').pack(pady=(10, 5))
        name_entry = ttk.Entry(main_frame, width=40, font=('Helvetica', 12))
        name_entry.pack(pady=5)

        # Description
        ttk.Label(main_frame, text="Description", style='Metric.TLabel').pack(pady=(10, 5))
        desc_text = tk.Text(main_frame, height=3, width=40,
                            bg=self.colors['progress_bg'],
                            fg=self.colors['text'],
                            font=('Helvetica', 11))
        desc_text.pack(pady=5)

        # Metric selection
        ttk.Label(main_frame, text="Track Metric", style='Metric.TLabel').pack(pady=(10, 5))
        metric_var = tk.StringVar()
        metrics = ['steps', 'calories', 'workouts', 'distance', 'water']
        metric_combo = ttk.Combobox(main_frame, textvariable=metric_var, values=metrics,
                                    width=38, state='readonly')
        metric_combo.pack(pady=5)

        # Goal
        ttk.Label(main_frame, text="Daily Goal", style='Metric.TLabel').pack(pady=(10, 5))
        goal_entry = ttk.Entry(main_frame, width=40, font=('Helvetica', 12))
        goal_entry.pack(pady=5)

        # Duration
        ttk.Label(main_frame, text="Duration (days)", style='Metric.TLabel').pack(pady=(10, 5))
        duration_spin = tk.Spinbox(main_frame, from_=7, to=90, width=38,
                                   font=('Helvetica', 12))
        duration_spin.pack(pady=5)

        # Reward
        ttk.Label(main_frame, text="Reward", style='Metric.TLabel').pack(pady=(10, 5))
        reward_entry = ttk.Entry(main_frame, width=40, font=('Helvetica', 12))
        reward_entry.pack(pady=5)

        def save_challenge():
            challenge_data = {
                'id': len(self.db.data['challenges']) + 1,
                'name': name_entry.get(),
                'description': desc_text.get('1.0', 'end-1c'),
                'metric': metric_var.get(),
                'goal': int(goal_entry.get()),
                'duration': int(duration_spin.get()),
                'reward': reward_entry.get(),
                'created_by': self.current_user,
                'created_at': datetime.now().isoformat(),
                'participants': [self.current_user]
            }

            if not all(challenge_data.values()):
                messagebox.showerror("Error", "Please fill all fields")
                return

            self.db.data['challenges'].append(challenge_data)
            self.db.save_data()

            messagebox.showinfo("Success", "Challenge created successfully!")
            dialog.destroy()
            self.load_challenges()

        tk.Button(main_frame, text="Create Challenge",
                  bg=self.colors['success'],
                  fg=self.colors['text'],
                  font=('Helvetica', 14, 'bold'),
                  bd=0,
                  padx=40, pady=12,
                  cursor='hand2',
                  command=save_challenge).pack(pady=30)

    def create_library_tab(self):
        """Create exercise library tab"""
        frame = ttk.Frame(self.main_container, style='Dark.TFrame')

        # Header
        header = ttk.Frame(frame, style='Dark.TFrame')
        header.pack(fill='x', padx=30, pady=20)

        ttk.Label(header, text="📚 EXERCISE LIBRARY", style='Header.TLabel').pack(side='left')

        # Search bar
        search_frame = ttk.Frame(header, style='Dark.TFrame')
        search_frame.pack(side='right')

        ttk.Label(search_frame, text="🔍", style='Metric.TLabel',
                  font=('Helvetica', 14)).pack(side='left', padx=5)

        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var,
                                 width=30, font=('Helvetica', 12))
        search_entry.pack(side='left', padx=5)
        search_entry.bind('<KeyRelease>', self.filter_exercises)

        # Category filter
        self.category_var = tk.StringVar(value='All')
        categories = ['All', 'Cardio', 'Strength', 'Flexibility', 'Balance', 'HIIT']
        category_combo = ttk.Combobox(search_frame, textvariable=self.category_var,
                                      values=categories, width=15, state='readonly')
        category_combo.pack(side='left', padx=5)
        category_combo.bind('<<ComboboxSelected>>', self.filter_exercises)

        # Exercise list with scrollbar
        list_container = ttk.Frame(frame, style='Dark.TFrame')
        list_container.pack(fill='both', expand=True, padx=30, pady=10)

        # Create Treeview
        columns = ('Exercise', 'Category', 'Difficulty', 'Equipment', 'Calories/min')
        self.exercise_tree = ttk.Treeview(list_container, columns=columns, show='headings', height=20)

        # Define headings
        col_widths = [200, 100, 100, 150, 100]
        for col, width in zip(columns, col_widths):
            self.exercise_tree.heading(col, text=col)
            self.exercise_tree.column(col, width=width)

        # Add scrollbars
        vsb = ttk.Scrollbar(list_container, orient='vertical', command=self.exercise_tree.yview)
        hsb = ttk.Scrollbar(list_container, orient='horizontal', command=self.exercise_tree.xview)
        self.exercise_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # Grid layout
        self.exercise_tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')

        list_container.grid_rowconfigure(0, weight=1)
        list_container.grid_columnconfigure(0, weight=1)

        # Load exercises
        self.load_exercises()

        # Bind double-click
        self.exercise_tree.bind('<Double-1>', self.view_exercise_details)

        return frame

    def load_exercises(self):
        """Load exercises into library"""
        exercises = [
            ('Running', 'Cardio', 'Beginner', 'None', '10-12'),
            ('Jumping Jacks', 'Cardio', 'Beginner', 'None', '8-10'),
            ('Push-ups', 'Strength', 'Intermediate', 'None', '5-7'),
            ('Squats', 'Strength', 'Beginner', 'None', '6-8'),
            ('Plank', 'Strength', 'Intermediate', 'None', '3-4'),
            ('Yoga', 'Flexibility', 'Beginner', 'Mat', '3-5'),
            ('Burpees', 'HIIT', 'Advanced', 'None', '12-15'),
            ('Mountain Climbers', 'Cardio', 'Intermediate', 'None', '8-10'),
            ('Lunges', 'Strength', 'Beginner', 'None', '5-7'),
            ('Pull-ups', 'Strength', 'Advanced', 'Bar', '6-8'),
            ('Swimming', 'Cardio', 'Intermediate', 'Pool', '8-10'),
            ('Cycling', 'Cardio', 'Beginner', 'Bike', '7-9'),
            ('Deadlifts', 'Strength', 'Advanced', 'Barbell', '5-7'),
            ('Bench Press', 'Strength', 'Intermediate', 'Barbell', '5-7'),
            ('Shoulder Press', 'Strength', 'Intermediate', 'Dumbbells', '5-7'),
        ]

        for exercise in exercises:
            self.exercise_tree.insert('', 'end', values=exercise)

    def filter_exercises(self, event=None):
        """Filter exercises based on search and category"""
        search_term = self.search_var.get().lower()
        category = self.category_var.get()

        # Clear existing
        for item in self.exercise_tree.get_children():
            self.exercise_tree.delete(item)

        # Reload with filter
        exercises = [
            ('Running', 'Cardio', 'Beginner', 'None', '10-12'),
            ('Jumping Jacks', 'Cardio', 'Beginner', 'None', '8-10'),
            ('Push-ups', 'Strength', 'Intermediate', 'None', '5-7'),
            ('Squats', 'Strength', 'Beginner', 'None', '6-8'),
            ('Plank', 'Strength', 'Intermediate', 'None', '3-4'),
            ('Yoga', 'Flexibility', 'Beginner', 'Mat', '3-5'),
            ('Burpees', 'HIIT', 'Advanced', 'None', '12-15'),
            ('Mountain Climbers', 'Cardio', 'Intermediate', 'None', '8-10'),
            ('Lunges', 'Strength', 'Beginner', 'None', '5-7'),
            ('Pull-ups', 'Strength', 'Advanced', 'Bar', '6-8'),
            ('Swimming', 'Cardio', 'Intermediate', 'Pool', '8-10'),
            ('Cycling', 'Cardio', 'Beginner', 'Bike', '7-9'),
            ('Deadlifts', 'Strength', 'Advanced', 'Barbell', '5-7'),
            ('Bench Press', 'Strength', 'Intermediate', 'Barbell', '5-7'),
            ('Shoulder Press', 'Strength', 'Intermediate', 'Dumbbells', '5-7'),
        ]

        for exercise in exercises:
            if category != 'All' and exercise[1] != category:
                continue
            if search_term and search_term not in exercise[0].lower():
                continue
            self.exercise_tree.insert('', 'end', values=exercise)

    def view_exercise_details(self, event):
        """View exercise details on double-click"""
        selection = self.exercise_tree.selection()
        if not selection:
            return

        item = self.exercise_tree.item(selection[0])
        values = item['values']

        dialog = tk.Toplevel(self.root)
        dialog.title(f"Exercise Details - {values[0]}")
        dialog.geometry("500x400")
        dialog.configure(bg=self.colors['bg'])

        main_frame = ttk.Frame(dialog, style='Card.TFrame')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        # Exercise name
        ttk.Label(main_frame, text=values[0],
                  style='Value.TLabel', font=('Helvetica', 24)).pack(pady=20)

        # Details
        details = [
            ('Category', values[1]),
            ('Difficulty', values[2]),
            ('Equipment', values[3]),
            ('Calories/min', values[4]),
        ]

        for label, value in details:
            frame = ttk.Frame(main_frame, style='Card.TFrame')
            frame.pack(fill='x', pady=10)

            ttk.Label(frame, text=label, style='Metric.TLabel',
                      font=('Helvetica', 14)).pack(side='left')
            ttk.Label(frame, text=value, style='SmallValue.TLabel',
                      font=('Helvetica', 14)).pack(side='right')

        # Instructions
        ttk.Label(main_frame, text="Instructions:", style='Title.TLabel').pack(anchor='w', pady=(20, 10))

        instructions = tk.Text(main_frame, height=6, width=50,
                               bg=self.colors['progress_bg'],
                               fg=self.colors['text'],
                               font=('Helvetica', 11))
        instructions.pack(fill='x', pady=5)
        instructions.insert('1.0', "Step-by-step instructions would appear here...")
        instructions.config(state='disabled')

        # Add to workout button
        tk.Button(main_frame, text="Add to Workout",
                  bg=self.colors['success'],
                  fg=self.colors['text'],
                  font=('Helvetica', 12, 'bold'),
                  bd=0,
                  padx=30, pady=10,
                  cursor='hand2',
                  command=lambda: self.add_exercise_to_workout(values[0])).pack(pady=20)

    def add_exercise_to_workout(self, exercise_name):
        """Add exercise to current workout"""
        if not self.current_user:
            messagebox.showinfo("Login Required", "Please login to add exercises")
            return

        # This would integrate with workout logging
        messagebox.showinfo("Success", f"Added {exercise_name} to your workout!")

    def create_social_tab(self):
        """Create social tab"""
        frame = ttk.Frame(self.main_container, style='Dark.TFrame')

        # Header
        header = ttk.Frame(frame, style='Dark.TFrame')
        header.pack(fill='x', padx=30, pady=20)

        ttk.Label(header, text="👥 SOCIAL FITNESS", style='Header.TLabel').pack(side='left')

        # Friend search
        search_frame = ttk.Frame(header, style='Dark.TFrame')
        search_frame.pack(side='right')

        ttk.Label(search_frame, text="Find Friends:", style='Metric.TLabel').pack(side='left', padx=5)

        self.friend_search_var = tk.StringVar()
        friend_entry = ttk.Entry(search_frame, textvariable=self.friend_search_var,
                                 width=20, font=('Helvetica', 11))
        friend_entry.pack(side='left', padx=5)
        friend_entry.bind('<Return>', self.search_friends)

        # Main content - two columns
        content_frame = ttk.Frame(frame, style='Dark.TFrame')
        content_frame.pack(fill='both', expand=True, padx=30, pady=10)

        # Left column - Friends list
        left_col = ttk.Frame(content_frame, style='Dark.TFrame')
        left_col.pack(side='left', fill='both', expand=True, padx=(0, 10))

        friends_card = ttk.Frame(left_col, style='Card.TFrame')
        friends_card.pack(fill='both', expand=True)

        ttk.Label(friends_card, text="Friends", style='Title.TLabel').pack(anchor='w', padx=15, pady=(15, 10))

        # Friends list
        self.friends_list = ttk.Frame(friends_card, style='Card.TFrame')
        self.friends_list.pack(fill='both', expand=True, padx=15, pady=10)

        # Sample friends
        friends = [
            ('John Doe', '🏃 Running', 'Online', self.colors['success']),
            ('Jane Smith', '💪 Strength', 'Offline', self.colors['text_secondary']),
            ('Mike Johnson', '🚴 Cycling', 'Online', self.colors['success']),
        ]

        for name, activity, status, color in friends:
            self.create_friend_item(self.friends_list, name, activity, status, color)

        # Right column - Activity feed
        right_col = ttk.Frame(content_frame, style='Dark.TFrame')
        right_col.pack(side='right', fill='both', expand=True, padx=(10, 0))

        feed_card = ttk.Frame(right_col, style='Card.TFrame')
        feed_card.pack(fill='both', expand=True)

        ttk.Label(feed_card, text="Activity Feed", style='Title.TLabel').pack(anchor='w', padx=15, pady=(15, 10))

        # Feed list
        feed_list = ttk.Frame(feed_card, style='Card.TFrame')
        feed_list.pack(fill='both', expand=True, padx=15, pady=10)

        # Sample activities
        activities = [
            ('John completed a 5K run', '10 min ago'),
            ('Jane set a new PR in bench press', '25 min ago'),
            ('Mike joined the 10K steps challenge', '1 hour ago'),
            ('Sarah started a new workout plan', '2 hours ago'),
        ]

        for activity, time in activities:
            self.create_feed_item(feed_list, activity, time)

        return frame

    def create_friend_item(self, parent, name, activity, status, color):
        """Create friend list item"""
        frame = tk.Frame(parent, bg=self.colors['progress_bg'],
                         height=70)
        frame.pack(fill='x', pady=5)
        frame.pack_propagate(False)

        # Status indicator
        status_indicator = tk.Label(frame, text="●",
                                    bg=self.colors['progress_bg'],
                                    fg=color,
                                    font=('Helvetica', 15))
        status_indicator.pack(side='left', padx=10)

        # Friend info
        info_frame = tk.Frame(frame, bg=self.colors['progress_bg'])
        info_frame.pack(side='left', fill='both', expand=True)

        tk.Label(info_frame, text=name,
                 bg=self.colors['progress_bg'],
                 fg=self.colors['text'],
                 font=('Helvetica', 12, 'bold')).pack(anchor='w')

        tk.Label(info_frame, text=activity,
                 bg=self.colors['progress_bg'],
                 fg=self.colors['text_secondary'],
                 font=('Helvetica', 10)).pack(anchor='w')

        # Message button
        tk.Button(frame, text="💬",
                  bg=self.colors['card_bg'],
                  fg=self.colors['text'],
                  font=('Helvetica', 12),
                  bd=0,
                  width=3,
                  cursor='hand2').pack(side='right', padx=10)

    def create_feed_item(self, parent, activity, time):
        """Create feed item"""
        frame = tk.Frame(parent, bg=self.colors['progress_bg'],
                         height=60)
        frame.pack(fill='x', pady=5)
        frame.pack_propagate(False)

        tk.Label(frame, text="👤",
                 bg=self.colors['progress_bg'],
                 fg=self.colors['text'],
                 font=('Helvetica', 15)).pack(side='left', padx=10)

        text_frame = tk.Frame(frame, bg=self.colors['progress_bg'])
        text_frame.pack(side='left', fill='both', expand=True)

        tk.Label(text_frame, text=activity,
                 bg=self.colors['progress_bg'],
                 fg=self.colors['text'],
                 font=('Helvetica', 11)).pack(anchor='w')

        tk.Label(text_frame, text=time,
                 bg=self.colors['progress_bg'],
                 fg=self.colors['text_secondary'],
                 font=('Helvetica', 9)).pack(anchor='w')

    def search_friends(self, event=None):
        """Search for friends"""
        search_term = self.friend_search_var.get()
        if search_term:
            messagebox.showinfo("Search", f"Searching for '{search_term}'...")

    def create_settings_tab(self):
        """Create settings tab"""
        frame = ttk.Frame(self.main_container, style='Dark.TFrame')

        if not self.current_user:
            # Show login prompt
            center_frame = ttk.Frame(frame, style='Dark.TFrame')
            center_frame.pack(expand=True)

            ttk.Label(center_frame, text="Please login to access settings",
                      style='Value.TLabel', font=('Helvetica', 18)).pack(pady=20)

            tk.Button(center_frame, text="Login",
                      bg=self.colors['success'],
                      fg=self.colors['text'],
                      font=('Helvetica', 14, 'bold'),
                      bd=0,
                      padx=40, pady=12,
                      cursor='hand2',
                      command=self.show_profile).pack()
            return frame

        # Settings content
        settings_frame = ttk.Frame(frame, style='Dark.TFrame')
        settings_frame.pack(fill='both', expand=True, padx=30, pady=20)

        # Profile Settings
        profile_card = ttk.Frame(settings_frame, style='Card.TFrame')
        profile_card.pack(fill='x', pady=(0, 20))

        ttk.Label(profile_card, text="Profile Settings", style='Title.TLabel').pack(anchor='w', padx=15, pady=(15, 10))

        # Profile form
        form_frame = ttk.Frame(profile_card, style='Card.TFrame')
        form_frame.pack(fill='x', padx=15, pady=10)

        fields = [
            ('Age', 'age'),
            ('Weight (kg)', 'weight'),
            ('Height (cm)', 'height'),
            ('Gender', 'gender'),
        ]

        self.settings_entries = {}
        user_data = self.db.data['users'][self.current_user]['profile']

        for label, key in fields:
            row = ttk.Frame(form_frame, style='Card.TFrame')
            row.pack(fill='x', pady=5)

            ttk.Label(row, text=label, style='Metric.TLabel').pack(side='left')

            entry = ttk.Entry(row, width=20, font=('Helvetica', 12))
            entry.pack(side='right')
            entry.insert(0, user_data.get(key, ''))
            self.settings_entries[key] = entry

        # Notification Settings
        notif_card = ttk.Frame(settings_frame, style='Card.TFrame')
        notif_card.pack(fill='x', pady=(0, 20))

        ttk.Label(notif_card, text="Notification Settings", style='Title.TLabel').pack(anchor='w', padx=15,
                                                                                       pady=(15, 10))

        notif_frame = ttk.Frame(notif_card, style='Card.TFrame')
        notif_frame.pack(fill='x', padx=15, pady=10)

        self.notif_vars = {}
        notifications = [
            ('Workout Reminders', 'workout_reminders'),
            ('Achievement Alerts', 'achievement_alerts'),
            ('Challenge Updates', 'challenge_updates'),
            ('Friend Activity', 'friend_activity'),
        ]

        for label, key in notifications:
            var = tk.BooleanVar(value=True)
            self.notif_vars[key] = var
            cb = tk.Checkbutton(notif_frame, text=label, variable=var,
                                bg=self.colors['card_bg'],
                                fg=self.colors['text'],
                                selectcolor=self.colors['card_bg'],
                                font=('Helvetica', 11))
            cb.pack(anchor='w', pady=5)

        # Units Settings
        units_card = ttk.Frame(settings_frame, style='Card.TFrame')
        units_card.pack(fill='x', pady=(0, 20))

        ttk.Label(units_card, text="Units", style='Title.TLabel').pack(anchor='w', padx=15, pady=(15, 10))

        units_frame = ttk.Frame(units_card, style='Card.TFrame')
        units_frame.pack(fill='x', padx=15, pady=10)

        self.units_var = tk.StringVar(value='metric')
        tk.Radiobutton(units_frame, text="Metric (kg, km)", variable=self.units_var,
                       value='metric', bg=self.colors['card_bg'],
                       fg=self.colors['text'],
                       selectcolor=self.colors['card_bg'],
                       font=('Helvetica', 11)).pack(anchor='w', pady=5)
        tk.Radiobutton(units_frame, text="Imperial (lbs, miles)", variable=self.units_var,
                       value='imperial', bg=self.colors['card_bg'],
                       fg=self.colors['text'],
                       selectcolor=self.colors['card_bg'],
                       font=('Helvetica', 11)).pack(anchor='w', pady=5)

        # Save button
        def save_settings():
            # Update profile
            for key, entry in self.settings_entries.items():
                self.db.data['users'][self.current_user]['profile'][key] = entry.get()

            # Update notification settings
            for key, var in self.notif_vars.items():
                if 'settings' not in self.db.data['users'][self.current_user]:
                    self.db.data['users'][self.current_user]['settings'] = {}
                self.db.data['users'][self.current_user]['settings'][key] = var.get()

            # Update units
            self.db.data['users'][self.current_user]['settings']['units'] = self.units_var.get()

            self.db.save_data()
            messagebox.showinfo("Success", "Settings saved successfully!")

        tk.Button(settings_frame, text="Save Settings",
                  bg=self.colors['success'],
                  fg=self.colors['text'],
                  font=('Helvetica', 14, 'bold'),
                  bd=0,
                  padx=40, pady=12,
                  cursor='hand2',
                  command=save_settings).pack(pady=20)

        # Data export
        export_card = ttk.Frame(settings_frame, style='Card.TFrame')
        export_card.pack(fill='x')

        ttk.Label(export_card, text="Data Management", style='Title.TLabel').pack(anchor='w', padx=15, pady=(15, 10))

        export_frame = ttk.Frame(export_card, style='Card.TFrame')
        export_frame.pack(fill='x', padx=15, pady=10)

        tk.Button(export_frame, text="Export Data (CSV)",
                  bg=self.colors['info'],
                  fg=self.colors['text'],
                  font=('Helvetica', 11),
                  bd=0,
                  padx=20, pady=8,
                  cursor='hand2',
                  command=self.export_user_data).pack(side='left', padx=5)

        tk.Button(export_frame, text="Generate Report (PDF)",
                  bg=self.colors['warning'],
                  fg=self.colors['text'],
                  font=('Helvetica', 11),
                  bd=0,
                  padx=20, pady=8,
                  cursor='hand2',
                  command=self.generate_user_report).pack(side='left', padx=5)

        tk.Button(export_frame, text="Delete Account",
                  bg=self.colors['accent'],
                  fg=self.colors['text'],
                  font=('Helvetica', 11),
                  bd=0,
                  padx=20, pady=8,
                  cursor='hand2',
                  command=self.delete_account).pack(side='right', padx=5)

        return frame

    def update_settings_tab(self):
        """Update settings tab when shown"""
        # This will refresh the settings tab when user logs in
        pass

    def export_user_data(self):
        """Export user data to CSV"""
        if not self.current_user:
            return

        filename = filedialog.asksaveasfilename(
            defaultextension='.csv',
            filetypes=[('CSV files', '*.csv')],
            initialfile=f'{self.current_user}_data_{datetime.now().strftime("%Y%m%d")}.csv'
        )

        if filename:
            # Get user workouts
            workouts = self.db.get_user_workouts(self.current_user, 365)

            # Create DataFrame
            df = pd.DataFrame(workouts)

            if not df.empty:
                df.to_csv(filename, index=False)
                messagebox.showinfo("Success", f"Data exported to {filename}")

    def generate_user_report(self):
        """Generate PDF report for user"""
        if not self.current_user:
            return

        filename = filedialog.asksaveasfilename(
            defaultextension='.pdf',
            filetypes=[('PDF files', '*.pdf')],
            initialfile=f'{self.current_user}_report_{datetime.now().strftime("%Y%m%d")}.pdf'
        )

        if filename:
            try:
                report_path = self.report_generator.generate_weekly_report(self.current_user, filename)
                if report_path:
                    messagebox.showinfo("Success", f"Report generated: {report_path}")
                else:
                    messagebox.showerror("Error", "ReportLab not installed. Please install reportlab to generate PDFs.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to generate report: {e}")

    def delete_account(self):
        """Delete user account"""
        response = messagebox.askyesno("Delete Account",
                                       "Are you sure you want to delete your account? This cannot be undone!")
        if response:
            # Remove user data
            del self.db.data['users'][self.current_user]
            self.db.save_data()

            self.current_user = None
            self.profile_btn.config(text="👤")
            messagebox.showinfo("Account Deleted", "Your account has been deleted.")
            self.show_tab(0)

    def quick_action(self, action):
        """Handle quick action buttons"""
        if action == '📄 Report':
            self.generate_user_report()
            return

        if not self.current_user:
            messagebox.showinfo("Login Required", "Please login to use this feature")
            self.show_profile()
            return

        if action == '📊 Log Workout':
            self.show_workout_dialog()
        elif action == '💧 Water':
            self.show_water_dialog()
        elif action == '😴 Sleep':
            self.show_sleep_dialog()
        elif action == '⚖️ Weight':
            self.show_weight_dialog()

    def show_workout_dialog(self):
        """Show workout logging dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Log Workout")
        dialog.geometry("500x600")
        dialog.configure(bg=self.colors['bg'])

        main_frame = ttk.Frame(dialog, style='Card.TFrame')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        ttk.Label(main_frame, text="Log Your Workout",
                  style='Value.TLabel', font=('Helvetica', 20)).pack(pady=20)

        # Workout type
        ttk.Label(main_frame, text="Workout Type", style='Metric.TLabel').pack(pady=(10, 5))
        type_var = tk.StringVar()
        types = ['Running', 'Cycling', 'Swimming', 'Strength Training', 'Yoga', 'Walking', 'HIIT']
        type_combo = ttk.Combobox(main_frame, textvariable=type_var, values=types,
                                  width=38, state='readonly')
        type_combo.pack(pady=5)

        # Duration
        ttk.Label(main_frame, text="Duration (minutes)", style='Metric.TLabel').pack(pady=(10, 5))
        duration_spin = tk.Spinbox(main_frame, from_=1, to=300, width=38,
                                   font=('Helvetica', 12))
        duration_spin.pack(pady=5)

        # Distance
        ttk.Label(main_frame, text="Distance (km)", style='Metric.TLabel').pack(pady=(10, 5))
        distance_entry = ttk.Entry(main_frame, width=40, font=('Helvetica', 12))
        distance_entry.pack(pady=5)

        # Calories
        ttk.Label(main_frame, text="Calories Burned", style='Metric.TLabel').pack(pady=(10, 5))
        calories_spin = tk.Spinbox(main_frame, from_=0, to=2000, width=38,
                                   font=('Helvetica', 12))
        calories_spin.pack(pady=5)

        # Intensity
        ttk.Label(main_frame, text="Intensity", style='Metric.TLabel').pack(pady=(10, 5))
        intensity_var = tk.StringVar(value='Medium')
        intensity_frame = ttk.Frame(main_frame, style='Card.TFrame')
        intensity_frame.pack(pady=5)

        for intensity in ['Low', 'Medium', 'High']:
            rb = tk.Radiobutton(intensity_frame, text=intensity, variable=intensity_var,
                                value=intensity, bg=self.colors['card_bg'],
                                fg=self.colors['text'],
                                selectcolor=self.colors['card_bg'])
            rb.pack(side='left', padx=10)

        # Notes
        ttk.Label(main_frame, text="Notes", style='Metric.TLabel').pack(pady=(10, 5))
        notes_text = tk.Text(main_frame, height=3, width=40,
                             bg=self.colors['progress_bg'],
                             fg=self.colors['text'],
                             font=('Helvetica', 11))
        notes_text.pack(pady=5)

        def save_workout():
            workout_data = {
                'type': type_var.get(),
                'duration': int(duration_spin.get()),
                'distance': float(distance_entry.get()) if distance_entry.get() else 0,
                'calories': int(calories_spin.get()),
                'intensity': intensity_var.get(),
                'notes': notes_text.get('1.0', 'end-1c')
            }

            if not workout_data['type']:
                messagebox.showerror("Error", "Please select workout type")
                return

            workout_id = self.db.add_workout(self.current_user, workout_data)

            # Add notification
            self.notification_manager.add_notification(
                self.current_user,
                "Workout Logged!",
                f"Great job! You logged a {workout_data['duration']} minute {workout_data['type']} session.",
                'success'
            )

            messagebox.showinfo("Success", "Workout logged successfully!")
            dialog.destroy()

            # Update dashboard
            self.update_dashboard()
            self.update_workouts_tab()

        tk.Button(main_frame, text="Save Workout",
                  bg=self.colors['success'],
                  fg=self.colors['text'],
                  font=('Helvetica', 14, 'bold'),
                  bd=0,
                  padx=40, pady=12,
                  cursor='hand2',
                  command=save_workout).pack(pady=20)

    def show_water_dialog(self):
        """Show water intake dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Log Water Intake")
        dialog.geometry("400x300")
        dialog.configure(bg=self.colors['bg'])

        main_frame = ttk.Frame(dialog, style='Card.TFrame')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        ttk.Label(main_frame, text="💧 Water Intake",
                  style='Value.TLabel', font=('Helvetica', 20)).pack(pady=20)

        ttk.Label(main_frame, text="Amount (ml)", style='Metric.TLabel').pack(pady=(10, 5))

        water_var = tk.IntVar(value=250)
        water_spin = tk.Spinbox(main_frame, from_=50, to=1000, increment=50,
                                textvariable=water_var, width=20,
                                font=('Helvetica', 14))
        water_spin.pack(pady=5)

        # Quick add buttons
        quick_frame = ttk.Frame(main_frame, style='Card.TFrame')
        quick_frame.pack(pady=20)

        for amount in [250, 500, 750]:
            btn = tk.Button(quick_frame, text=f"{amount}ml",
                            bg=self.colors['info'],
                            fg=self.colors['text'],
                            font=('Helvetica', 11),
                            bd=0,
                            padx=15, pady=8,
                            cursor='hand2',
                            command=lambda a=amount: water_var.set(a))
            btn.pack(side='left', padx=5)

        def save_water():
            amount = water_var.get()

            # Add notification
            self.notification_manager.add_notification(
                self.current_user,
                "Water Logged",
                f"You've logged {amount}ml of water. Stay hydrated!",
                'info'
            )

            messagebox.showinfo("Success", f"Logged {amount}ml of water!")
            dialog.destroy()

        tk.Button(main_frame, text="Log Water",
                  bg=self.colors['success'],
                  fg=self.colors['text'],
                  font=('Helvetica', 14, 'bold'),
                  bd=0,
                  padx=40, pady=12,
                  cursor='hand2',
                  command=save_water).pack(pady=10)

    def show_sleep_dialog(self):
        """Show sleep logging dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Log Sleep")
        dialog.geometry("400x400")
        dialog.configure(bg=self.colors['bg'])

        main_frame = ttk.Frame(dialog, style='Card.TFrame')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        ttk.Label(main_frame, text="😴 Sleep Log",
                  style='Value.TLabel', font=('Helvetica', 20)).pack(pady=20)

        # Sleep time
        ttk.Label(main_frame, text="Hours Slept", style='Metric.TLabel').pack(pady=(10, 5))

        hours_var = tk.DoubleVar(value=7.5)
        hours_spin = tk.Spinbox(main_frame, from_=0, to=24, increment=0.5,
                                textvariable=hours_var, width=20,
                                font=('Helvetica', 14))
        hours_spin.pack(pady=5)

        # Sleep quality
        ttk.Label(main_frame, text="Sleep Quality", style='Metric.TLabel').pack(pady=(10, 5))

        quality_var = tk.StringVar(value='Good')
        quality_frame = ttk.Frame(main_frame, style='Card.TFrame')
        quality_frame.pack(pady=5)

        for quality in ['Poor', 'Fair', 'Good', 'Excellent']:
            rb = tk.Radiobutton(quality_frame, text=quality, variable=quality_var,
                                value=quality, bg=self.colors['card_bg'],
                                fg=self.colors['text'],
                                selectcolor=self.colors['card_bg'])
            rb.pack(anchor='w')

        def save_sleep():
            hours = hours_var.get()
            quality = quality_var.get()

            messagebox.showinfo("Success", f"Logged {hours} hours of sleep (Quality: {quality})")
            dialog.destroy()

        tk.Button(main_frame, text="Log Sleep",
                  bg=self.colors['success'],
                  fg=self.colors['text'],
                  font=('Helvetica', 14, 'bold'),
                  bd=0,
                  padx=40, pady=12,
                  cursor='hand2',
                  command=save_sleep).pack(pady=20)

    def show_weight_dialog(self):
        """Show weight logging dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Log Weight")
        dialog.geometry("400x350")
        dialog.configure(bg=self.colors['bg'])

        main_frame = ttk.Frame(dialog, style='Card.TFrame')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        ttk.Label(main_frame, text="⚖️ Weight Log",
                  style='Value.TLabel', font=('Helvetica', 20)).pack(pady=20)

        ttk.Label(main_frame, text="Weight (kg)", style='Metric.TLabel').pack(pady=(10, 5))

        weight_var = tk.DoubleVar(value=75.0)
        weight_spin = tk.Spinbox(main_frame, from_=30, to=200, increment=0.1,
                                 textvariable=weight_var, width=20,
                                 font=('Helvetica', 14))
        weight_spin.pack(pady=5)

        # Notes
        ttk.Label(main_frame, text="Notes", style='Metric.TLabel').pack(pady=(10, 5))
        notes_entry = ttk.Entry(main_frame, width=30, font=('Helvetica', 11))
        notes_entry.pack(pady=5)

        def save_weight():
            weight = weight_var.get()
            notes = notes_entry.get()

            messagebox.showinfo("Success", f"Logged weight: {weight} kg")
            dialog.destroy()

        tk.Button(main_frame, text="Log Weight",
                  bg=self.colors['success'],
                  fg=self.colors['text'],
                  font=('Helvetica', 14, 'bold'),
                  bd=0,
                  padx=40, pady=12,
                  cursor='hand2',
                  command=save_weight).pack(pady=20)

    def add_to_schedule(self):
        """Add workout to schedule"""
        if not self.current_user:
            messagebox.showinfo("Login Required", "Please login to use this feature")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Add to Schedule")
        dialog.geometry("500x400")
        dialog.configure(bg=self.colors['bg'])

        main_frame = ttk.Frame(dialog, style='Card.TFrame')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        ttk.Label(main_frame, text="Schedule Workout",
                  style='Value.TLabel', font=('Helvetica', 20)).pack(pady=20)

        # Date
        ttk.Label(main_frame, text="Date", style='Metric.TLabel').pack(pady=(10, 5))
        date_picker = DateEntry(main_frame, width=20, background='darkblue',
                                foreground='white', borderwidth=2)
        date_picker.pack(pady=5)

        # Time
        ttk.Label(main_frame, text="Time", style='Metric.TLabel').pack(pady=(10, 5))
        time_frame = ttk.Frame(main_frame, style='Card.TFrame')
        time_frame.pack(pady=5)

        hour_spin = tk.Spinbox(time_frame, from_=0, to=23, width=5,
                               format='%02.0f', font=('Helvetica', 12))
        hour_spin.pack(side='left', padx=2)
        ttk.Label(time_frame, text=":", style='Metric.TLabel').pack(side='left')
        minute_spin = tk.Spinbox(time_frame, from_=0, to=59, width=5,
                                 format='%02.0f', font=('Helvetica', 12))
        minute_spin.pack(side='left', padx=2)

        # Workout type
        ttk.Label(main_frame, text="Workout Type", style='Metric.TLabel').pack(pady=(10, 5))
        type_var = tk.StringVar()
        types = ['Running', 'Cycling', 'Swimming', 'Strength', 'Yoga', 'Walking']
        type_combo = ttk.Combobox(main_frame, textvariable=type_var, values=types,
                                  width=30, state='readonly')
        type_combo.pack(pady=5)

        def save_schedule():
            date = date_picker.get_date()
            time_str = f"{int(hour_spin.get()):02d}:{int(minute_spin.get()):02d}"
            workout_type = type_var.get()

            if not workout_type:
                messagebox.showerror("Error", "Please select workout type")
                return

            messagebox.showinfo("Success",
                                f"Workout scheduled for {date} at {time_str}")
            dialog.destroy()

        tk.Button(main_frame, text="Add to Schedule",
                  bg=self.colors['success'],
                  fg=self.colors['text'],
                  font=('Helvetica', 14, 'bold'),
                  bd=0,
                  padx=40, pady=12,
                  cursor='hand2',
                  command=save_schedule).pack(pady=20)

    def show_notifications(self):
        """Show notifications panel"""
        if not self.current_user:
            messagebox.showinfo("Login Required", "Please login to view notifications")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Notifications")
        dialog.geometry("400x500")
        dialog.configure(bg=self.colors['bg'])

        main_frame = ttk.Frame(dialog, style='Card.TFrame')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        ttk.Label(main_frame, text="Notifications",
                  style='Value.TLabel', font=('Helvetica', 18)).pack(pady=10)

        # Mark all read button
        def mark_all_read():
            for notif in self.notification_manager.get_user_notifications(self.current_user):
                notif['read'] = True
            self.show_notifications()  # Refresh

        tk.Button(main_frame, text="Mark All as Read",
                  bg=self.colors['info'],
                  fg=self.colors['text'],
                  font=('Helvetica', 10),
                  bd=0,
                  padx=15, pady=5,
                  cursor='hand2',
                  command=mark_all_read).pack(pady=5)

        # Notifications list
        notif_frame = ttk.Frame(main_frame, style='Card.TFrame')
        notif_frame.pack(fill='both', expand=True, pady=10)

        notifications = self.notification_manager.get_user_notifications(self.current_user)

        if not notifications:
            ttk.Label(notif_frame, text="No notifications",
                      style='Metric.TLabel').pack(pady=30)
        else:
            for notif in notifications:
                self.create_notification_detail(notif_frame, notif)

    def create_notification_detail(self, parent, notification):
        """Create detailed notification item"""
        frame = tk.Frame(parent, bg=self.colors['progress_bg'] if not notification['read'] else self.colors['card_bg'],
                         height=80)
        frame.pack(fill='x', pady=2)
        frame.pack_propagate(False)

        # Indicator
        colors = {
            'info': self.colors['info'],
            'success': self.colors['success'],
            'warning': self.colors['warning'],
            'reminder': self.colors['accent']
        }

        indicator = tk.Label(frame, text="●",
                             bg=frame['bg'],
                             fg=colors.get(notification['type'], self.colors['info']),
                             font=('Helvetica', 15))
        indicator.pack(side='left', padx=10)

        # Content
        text_frame = tk.Frame(frame, bg=frame['bg'])
        text_frame.pack(side='left', fill='both', expand=True, padx=5)

        tk.Label(text_frame, text=notification['title'],
                 bg=frame['bg'],
                 fg=self.colors['text'],
                 font=('Helvetica', 11, 'bold')).pack(anchor='w')

        tk.Label(text_frame, text=notification['message'],
                 bg=frame['bg'],
                 fg=self.colors['text_secondary'],
                 font=('Helvetica', 9),
                 wraplength=200).pack(anchor='w')

        # Time
        time_str = datetime.fromisoformat(notification['timestamp']).strftime('%H:%M %d/%m')
        tk.Label(frame, text=time_str,
                 bg=frame['bg'],
                 fg=self.colors['text_secondary'],
                 font=('Helvetica', 8)).pack(side='right', padx=10)

    def edit_workout(self, workout_values):
        """Edit workout"""
        messagebox.showinfo("Edit", "Edit workout functionality would go here")

    def delete_workout(self, workout_values):
        """Delete workout"""
        response = messagebox.askyesno("Delete", "Are you sure you want to delete this workout?")
        if response:
            messagebox.showinfo("Deleted", "Workout deleted successfully")

    def show_all_activity(self):
        """Show all activity"""
        messagebox.showinfo("Activity", "Full activity log would be shown here")

    def start_background_tasks(self):
        """Start background tasks"""

        def check_reminders():
            while True:
                time.sleep(60)  # Check every minute
                # Add reminder logic here
                pass

        thread = threading.Thread(target=check_reminders, daemon=True)
        thread.start()

    def export_progress_report(self):
        """Export progress report"""
        self.generate_user_report()

    def update_dashboard(self):
        """Update dashboard with user data"""
        if self.current_user:
            self.profile_btn.config(text="👤 ✓")
            # Refresh dashboard components
            # This would update all dashboard widgets with real data

    def update_plans_tab(self):
        """Update plans tab"""
        pass

    def update_challenges_tab(self):
        """Update challenges tab"""
        self.load_challenges()

    def update_social_tab(self):
        """Update social tab"""
        pass

    def show_profile(self):
        """Show profile/login dialog"""
        if not self.current_user:
            self.show_login_dialog()
        else:
            self.show_user_profile()

    def show_login_dialog(self):
        """Show login dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Login / Register")
        dialog.geometry("450x600")
        dialog.configure(bg=self.colors['bg'])

        # Create notebook for tabs
        notebook = ttk.Notebook(dialog)
        notebook.pack(fill='both', expand=True, padx=20, pady=20)

        # Login tab
        login_frame = ttk.Frame(notebook, style='Card.TFrame')
        notebook.add(login_frame, text="Login")

        ttk.Label(login_frame, text="Welcome Back!",
                  style='Value.TLabel', font=('Helvetica', 20)).pack(pady=30)

        ttk.Label(login_frame, text="Username", style='Metric.TLabel').pack(pady=(20, 5))
        username_entry = ttk.Entry(login_frame, width=30, font=('Helvetica', 12))
        username_entry.pack(pady=5)

        ttk.Label(login_frame, text="Password", style='Metric.TLabel').pack(pady=(10, 5))
        password_entry = ttk.Entry(login_frame, show="*", width=30, font=('Helvetica', 12))
        password_entry.pack(pady=5)

        def login():
            username = username_entry.get()
            password = password_entry.get()

            if self.db.verify_user(username, password):
                self.current_user = username
                dialog.destroy()
                self.profile_btn.config(text="👤 ✓")
                messagebox.showinfo("Success", f"Welcome back, {username}!")
                self.update_dashboard()
            else:
                messagebox.showerror("Error", "Invalid username or password")

        tk.Button(login_frame, text="Login",
                  bg=self.colors['success'],
                  fg=self.colors['text'],
                  font=('Helvetica', 12, 'bold'),
                  bd=0,
                  padx=30, pady=10,
                  cursor='hand2',
                  command=login).pack(pady=30)

        # Register tab
        register_frame = ttk.Frame(notebook, style='Card.TFrame')
        notebook.add(register_frame, text="Register")

        ttk.Label(register_frame, text="Create Account",
                  style='Value.TLabel', font=('Helvetica', 20)).pack(pady=20)

        fields = ['Username', 'Password', 'Confirm Password', 'Age', 'Weight (kg)', 'Height (cm)', 'Gender']
        entries = {}

        for field in fields:
            ttk.Label(register_frame, text=field, style='Metric.TLabel').pack(pady=(10, 2))
            entry = ttk.Entry(register_frame, show="*" if "Password" in field else "",
                              width=30, font=('Helvetica', 12))
            entry.pack(pady=2)
            entries[field] = entry

        def register():
            username = entries['Username'].get()
            password = entries['Password'].get()
            confirm = entries['Confirm Password'].get()

            if not username or not password:
                messagebox.showerror("Error", "Username and password required")
                return

            if password != confirm:
                messagebox.showerror("Error", "Passwords do not match")
                return

            user_data = {
                'age': entries['Age'].get(),
                'weight': entries['Weight (kg)'].get(),
                'height': entries['Height (cm)'].get(),
                'gender': entries['Gender'].get(),
            }

            if self.db.add_user(username, password, user_data):
                messagebox.showinfo("Success", "Account created! Please login.")
                notebook.select(0)
            else:
                messagebox.showerror("Error", "Username already exists")

        tk.Button(register_frame, text="Register",
                  bg=self.colors['info'],
                  fg=self.colors['text'],
                  font=('Helvetica', 12, 'bold'),
                  bd=0,
                  padx=30, pady=10,
                  cursor='hand2',
                  command=register).pack(pady=30)

    def show_user_profile(self):
        """Show user profile"""
        user = self.db.data['users'][self.current_user]

        dialog = tk.Toplevel(self.root)
        dialog.title("User Profile")
        dialog.geometry("500x600")
        dialog.configure(bg=self.colors['bg'])

        main_frame = ttk.Frame(dialog, style='Card.TFrame')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        # Profile header
        tk.Label(main_frame, text="👤",
                 bg=self.colors['card_bg'],
                 fg=self.colors['text'],
                 font=('Helvetica', 60)).pack(pady=20)

        tk.Label(main_frame, text=self.current_user,
                 bg=self.colors['card_bg'],
                 fg=self.colors['text'],
                 font=('Helvetica', 24, 'bold')).pack()

        # Stats
        stats_frame = tk.Frame(main_frame, bg=self.colors['card_bg'])
        stats_frame.pack(fill='x', padx=30, pady=30)

        stats = [
            ('Workouts', user['stats']['total_workouts']),
            ('Streak', f"{user['stats']['streak_days']} days"),
            ('Level', 'Intermediate'),
            ('Points', '2,450')
        ]

        for i in range(0, 4, 2):
            row = tk.Frame(stats_frame, bg=self.colors['card_bg'])
            row.pack(fill='x', pady=10)

            for j in range(2):
                if i + j < len(stats):
                    label, value = stats[i + j]
                    frame = tk.Frame(row, bg=self.colors['progress_bg'],
                                     width=150, height=80)
                    frame.pack(side='left', padx=5, expand=True)
                    frame.pack_propagate(False)

                    tk.Label(frame, text=str(value),
                             bg=self.colors['progress_bg'],
                             fg=self.colors['text'],
                             font=('Helvetica', 20, 'bold')).pack(expand=True)
                    tk.Label(frame, text=label,
                             bg=self.colors['progress_bg'],
                             fg=self.colors['text_secondary'],
                             font=('Helvetica', 10)).pack()

        # User info
        info_frame = tk.Frame(main_frame, bg=self.colors['card_bg'])
        info_frame.pack(fill='x', padx=30, pady=20)

        info_items = [
            ('Age', user['profile'].get('age', 'N/A')),
            ('Weight', f"{user['profile'].get('weight', 'N/A')} kg"),
            ('Height', f"{user['profile'].get('height', 'N/A')} cm"),
            ('Gender', user['profile'].get('gender', 'N/A')),
            ('Member Since', datetime.fromisoformat(user['created_at']).strftime('%Y-%m-%d'))
        ]

        for label, value in info_items:
            row = tk.Frame(info_frame, bg=self.colors['card_bg'])
            row.pack(fill='x', pady=5)

            tk.Label(row, text=label,
                     bg=self.colors['card_bg'],
                     fg=self.colors['text_secondary'],
                     font=('Helvetica', 12)).pack(side='left')

            tk.Label(row, text=value,
                     bg=self.colors['card_bg'],
                     fg=self.colors['text'],
                     font=('Helvetica', 12, 'bold')).pack(side='right')

        # Logout button
        def logout():
            self.current_user = None
            self.profile_btn.config(text="👤")
            dialog.destroy()
            messagebox.showinfo("Logged Out", "You have been logged out")
            self.show_tab(0)

        tk.Button(main_frame, text="Logout",
                  bg=self.colors['accent'],
                  fg=self.colors['text'],
                  font=('Helvetica', 12, 'bold'),
                  bd=0,
                  padx=40, pady=10,
                  cursor='hand2',
                  command=logout).pack(pady=20)


def main():
    root = tk.Tk()
    app = FitnessTrackerGroup8(root)

    # Center window on screen
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')

    root.mainloop()


if __name__ == "__main__":
    main()