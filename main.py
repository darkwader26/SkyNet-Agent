#!/usr/bin/env python3
"""SkyNet Agent — main entry point."""

import os
import sys
import argparse

# Ensure we can import skynet
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from skynet.agent import SkyNetAgent
from skynet.config import load_config, AgentConfig


def main():
    parser = argparse.ArgumentParser(description="SkyNet Agent")
    parser.add_argument("-m", "--model", help="Default model (e.g. 'openai/gpt-4o')")
    parser.add_argument("-r", "--resume", help="Resume a session by ID")
    parser.add_argument("--no-improve", action="store_true",
                        help="Disable self-improvement")
    parser.add_argument("--yolo", action="store_true",
                        help="Skip approval gates")
    parser.add_argument("-q", "--query", help="Single query mode (non-interactive)")
    parser.add_argument("--daemon", action="store_true",
                        help="Enable background daemon")
    parser.add_argument("--db", help="Path to memory database")
    parser.add_argument("--prompt", help="Path to system prompt file")
    parser.add_argument("--tools-dir", help="Path to tools directory")
    args = parser.parse_args()

    config = load_config()

    if args.model:
        config.default_model = args.model
    if args.no_improve:
        config.auto_improve = False
    if args.yolo:
        config.approval_mode = "off"
    if args.daemon:
        config.daemon_enabled = True
    if args.db:
        config.memory_db_path = args.db
    if args.prompt:
        config.system_prompt_path = args.prompt
    if args.tools_dir:
        config.tools_dir = args.tools_dir

    agent = SkyNetAgent(config)

    if args.resume:
        if not agent.resume_session(args.resume):
            print(f"❌ Session '{args.resume}' not found")
            sys.exit(1)

    if args.query:
        agent._handle_message(args.query)
        return

    if args.daemon:
        agent.start_daemon()

    agent.run()


if __name__ == "__main__":
    main()
