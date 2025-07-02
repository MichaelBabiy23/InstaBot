import json
import logging
from datetime import datetime
from typing import Optional

import requests
import yaml
from colorama import Fore, Style

from GramAddict.core.plugin_loader import Plugin

logger = logging.getLogger(__name__)


def _to_int_or_zero(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


def load_sessions(username) -> Optional[dict]:
    try:
        with open(f"accounts/{username}/sessions.json") as json_data:
            return json.load(json_data)
    except FileNotFoundError:
        logger.error(
            "No session data found. Skipping report generation."
        )
        return None


def load_telegram_config(username) -> Optional[dict]:
    try:
        with open(
            f"accounts/{username}/telegram.yml", "r", encoding="utf-8"
        ) as stream:
            return yaml.safe_load(stream)
    except FileNotFoundError as e:
        logger.error(f"Config not found: {e}")
        return None


def telegram_bot_send_text(bot_api_token, bot_chat_ID, text):
    try:
        method = "sendMessage"
        parse_mode = "markdown"
        params = {"text": text, "chat_id": bot_chat_ID, "parse_mode": parse_mode}
        url = (
            f"https://api.telegram.org/bot{bot_api_token}/"
            f"{method}"
        )
        return requests.get(url, params=params).json()
    except Exception as e:
        logger.error(f"Telegram send error: {e}")
        return None


def _initialize_aggregated_data():
    return {
        "total_likes": 0,
        "total_comments": 0,
        "total_followed": 0,
        "total_unfollowed": 0,
        "total_watched": 0,
        "total_pm": 0,
        "duration": 0,
        "followers": 0,
        "following": 0,
        "followers_gained": 0,
    }


def _calculate_session_duration(session):
    try:
        start_datetime = datetime.strptime(
            session["start_time"], "%Y-%m-%d %H:%M:%S.%f"
        )
        finish_datetime = datetime.strptime(
            session["finish_time"], "%Y-%m-%d %H:%M:%S.%f"
        )
        return int((finish_datetime - start_datetime).total_seconds() / 60)
    except ValueError:
        logger.debug(
            f"{session['id']} has no finish_time. "
            f"Skipping duration calculation."
        )
        return 0


def daily_summary(sessions):
    daily_aggregated_data = {}
    for session in sessions:
        date = session["start_time"][:10]
        daily_aggregated_data.setdefault(date, _initialize_aggregated_data())
        duration = _calculate_session_duration(session)
        daily_aggregated_data[date]["duration"] += duration

        for key in [
            "total_likes",
            "total_watched",
            "total_followed",
            "total_unfollowed",
            "total_comments",
            "total_pm",
        ]:
            daily_aggregated_data[date][key] += session.get(key, 0)

        followers_session_val = _to_int_or_zero(session.get("profile", {}).get("followers"))
        followers_agg_val = _to_int_or_zero(daily_aggregated_data[date]["followers"])
        logger.debug(f"Comparing followers: session={followers_session_val} (type: {type(followers_session_val)}), aggregated={followers_agg_val} (type: {type(followers_agg_val)})")
        daily_aggregated_data[date]["followers"] = min(
            followers_session_val,
            followers_agg_val,
        )

        following_session_val = _to_int_or_zero(session.get("profile", {}).get("following"))
        following_agg_val = _to_int_or_zero(daily_aggregated_data[date]["following"])
        logger.debug(f"Comparing following: session={following_session_val} (type: {type(following_session_val)}), aggregated={following_agg_val} (type: {type(following_agg_val)})")
        daily_aggregated_data[date]["following"] = min(
            following_session_val,
            following_agg_val,
        )
    return _calculate_followers_gained(daily_aggregated_data)


def _calculate_followers_gained(aggregated_data):
    dates_sorted = sorted(aggregated_data.keys())
    previous_followers = None
    for date in dates_sorted:
        current_followers = aggregated_data[date]["followers"]
        if previous_followers is not None:
            followers_gained = current_followers - previous_followers
            aggregated_data[date]["followers_gained"] = followers_gained
        previous_followers = current_followers
    return aggregated_data


def generate_report(
    username,
    last_session,
    daily_aggregated_data,
    weekly_average_data,
    followers_now,
    following_now,
):
    followers_diff = followers_now - _to_int_or_zero(last_session.get("profile", {}).get(
        "followers"
    ))
    following_diff = following_now - _to_int_or_zero(last_session.get("profile", {}).get(
        "following"
    ))

    weekly_avg_duration = weekly_average_data["duration"] / 7
    weekly_avg_likes = weekly_average_data["total_likes"] / 7
    weekly_avg_followed = weekly_average_data["total_followed"] / 7
    weekly_avg_unfollowed = weekly_average_data["total_unfollowed"] / 7
    weekly_avg_watched = weekly_average_data["total_watched"] / 7
    weekly_avg_comments = weekly_average_data["total_comments"] / 7
    weekly_avg_pm = weekly_average_data["total_pm"] / 7

    return (
        f"""
            *Stats for {username}*

            *✨Overview after last activity*
            • {followers_now} followers ({followers_diff:+})
            • {following_now} following ({following_diff:+})

            *🤖 Last session actions*
            • {last_session["duration"]} minutes of botting
            • {last_session["total_likes"]} likes
            • {last_session["total_followed"]} follows
            • {last_session["total_unfollowed"]} unfollows
            • {last_session["total_watched"]} stories watched
            • {last_session["total_comments"]} comments done
            • {last_session["total_pm"]} PM sent

            *📅 Today\'s total actions*
            • {daily_aggregated_data["duration"]} minutes of botting
            • {daily_aggregated_data["total_likes"]} likes
            • {daily_aggregated_data["total_followed"]} follows
            • {daily_aggregated_data["total_unfollowed"]} unfollows
            • {daily_aggregated_data["total_watched"]} stories watched
            • {daily_aggregated_data["total_comments"]} comments done
            • {daily_aggregated_data["total_pm"]} PM sent

            *📈 Trends*
            • {daily_aggregated_data["followers_gained"]} new followers today
            • {weekly_average_data["followers_gained"]} new followers this week

            *🗓 7-Day Average*
            • {weekly_avg_duration:.0f} minutes of botting
            • {weekly_avg_likes:.0f} likes
            • {weekly_avg_followed:.0f} follows
            • {weekly_avg_unfollowed:.0f} unfollows
            • {weekly_avg_watched:.0f} stories watched
            • {weekly_avg_comments:.0f} comments done
            • {weekly_avg_pm:.0f} PM sent
        """
    )


def weekly_average(daily_aggregated_data, today) -> dict:
    weekly_average_data = _initialize_aggregated_data()

    for date in daily_aggregated_data:
        if (today - datetime.strptime(date, "%Y-%m-%d")).days > 7:
            continue
        for key in [
            "total_likes",
            "total_watched",
            "total_followed",
            "total_unfollowed",
            "total_comments",
            "total_pm",
            "duration",
        ]:
            weekly_average_data[key] += daily_aggregated_data[date][key]
        weekly_average_data["followers_gained"] += daily_aggregated_data[date].get("followers_gained", 0)
    return weekly_average_data


class TelegramReports(Plugin):
    """Generate reports at the end of the session and send them using telegram"""

    def __init__(self):
        super().__init__()
        self.description = (
            "Generate reports at the end of the session and send "
            "them using telegram. You have to configure 'telegram.yml' "
            "in your account folder"
        )
        self.arguments = [
            {
                "arg": "--telegram-reports",
                "help": (
                    "at the end of every session send a report to your "
                    "telegram account"
                ),
                "action": "store_true",
                "operation": True,
            }
        ]

    def run(self, config, plugin, followers_now, following_now, time_left):
        username = config.args.username
        if username is None:
            logger.error("You have to specify a username for getting reports!")
            return

        sessions = load_sessions(username)
        if not sessions:
            logger.error(
                f"No session data found for {username}. "
                "Skipping report generation."
            )
            return

        last_session = sessions[-1]
        last_session["duration"] = _calculate_session_duration(last_session)

        telegram_config = load_telegram_config(username)
        if not telegram_config:
            logger.error(
                f"No telegram config found for {username}. "
                "Skipping report generation."
            )
            return

        daily_aggregated_data = daily_summary(sessions)
        today_data = daily_aggregated_data.get(last_session["start_time"][:10], {})
        today = datetime.now()
        weekly_average_data = weekly_average(daily_aggregated_data, today)
        report = generate_report(
            username,
            last_session,
            today_data,
            weekly_average_data,
            followers_now,
            following_now,
        )
        response = telegram_bot_send_text(
            telegram_config.get("telegram-api-token"),
            telegram_config.get("telegram-chat-id"),
            report,
        )
        if response and response.get("ok"):
            logger.info(
                "Telegram message sent successfully.",
                extra={
                    "color": f"{Style.BRIGHT}{Fore.BLUE}"
                },
            )
        else:
            error = response.get("description") if response else "Unknown error"
            logger.error(
                f"Failed to send Telegram message: {error}"
            )
