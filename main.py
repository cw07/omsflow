import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

import structlog
from structlog.stdlib import ProcessorFormatter

from omsflow.core.oms import OrderManagementSystem
from omsflow.execution.broker import PhoenixBroker
from omsflow.sources.base import SQLOrderSource, RedisOrderSource
from omsflow.validation.engine import ValidationEngine, PriceValidationRule, PositionLimitRule


def setup_logging(log_level: str = "INFO") -> None:
    """Configure structured logging."""
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from JSON file."""
    with open(config_path, 'r') as f:
        return json.load(f)


async def main() -> None:
    parser = argparse.ArgumentParser(description="OMSFlow - Financial Order Management System")
    
    # Basic configuration
    parser.add_argument("--config", type=str, required=True, help="Path to configuration file")
    parser.add_argument("--log-level", type=str, default="INFO", help="Logging level")
    
    # Time window parameters
    parser.add_argument("--start-time", type=str, help="Start time (YYYY-MM-DD HH:MM:SS)")
    parser.add_argument("--end-time", type=str, help="End time (YYYY-MM-DD HH:MM:SS)")
    
    # Source selection
    parser.add_argument("--source", type=str, choices=["sql", "redis"], required=True, help="Order source type")
    
    # Broker selection
    parser.add_argument("--broker", type=str, choices=["phoenix", "futu"], required=True, help="Broker type")
    
    args = parser.parse_args()

    # Setup logging
    setup_logging(args.log_level)
    logger = structlog.get_logger()

    try:
        # Load configuration
        config = load_config(args.config)
        logger.info("configuration_loaded", config_path=args.config)

        # Parse time window
        start_time = datetime.strptime(args.start_time, "%Y-%m-%d %H:%M:%S") if args.start_time else None
        end_time = datetime.strptime(args.end_time, "%Y-%m-%d %H:%M:%S") if args.end_time else None

        # Create order source
        if args.source == "sql":
            order_source = SQLOrderSource(
                connection_string=config["sql"]["connection_string"]
            )
        else:  # redis
            order_source = RedisOrderSource(
                host=config["redis"]["host"],
                port=config["redis"]["port"],
                stream_key=config["redis"]["stream_key"]
            )

        # Create broker
        if args.broker == "phoenix":
            broker = PhoenixBroker(
                sender_comp_id=config["phoenix"]["sender_comp_id"],
                target_comp_id=config["phoenix"]["target_comp_id"],
                fix_config_path=config["phoenix"]["fix_config_path"],
                account=config["phoenix"]["account"]
            )
        else:  # futu
            # TODO: Implement Futu broker
            raise NotImplementedError("Futu broker not implemented yet")

        # Create validation engine
        validation_engine = ValidationEngine()
        validation_engine.add_rule(PriceValidationRule(
            max_price_deviation=config["validation"]["max_price_deviation"]
        ))
        validation_engine.add_rule(PositionLimitRule(
            max_position_value=config["validation"]["max_position_value"]
        ))

        # Create OMS
        oms = OrderManagementSystem(
            order_source=order_source,
            broker=broker,
            validation_engine=validation_engine,
            account=config["account"],
            broker_refdata=config["broker_refdata"]
        )

        # Start OMS
        logger.info("starting_oms", 
                   source=args.source,
                   broker=args.broker,
                   start_time=start_time,
                   end_time=end_time)
        
        await oms.start()

        # Keep running until interrupted
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("shutting_down")
            await oms.stop()

    except Exception as e:
        logger.error("fatal_error", error=str(e), exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main()) 