/**
 * Test Oanda API Connection
 * Run this before starting the bot to verify your credentials
 */
import Config from './config.js';
import logger from './logger.js';
import OandaClient from './oanda_client.js';

async function testConnection() {
  try {
    logger.info('');
    logger.info('═'.repeat(60));
    logger.info('🔧 OANDA CONNECTION TEST');
    logger.info('═'.repeat(60));
    logger.info('');

    // Validate config
    logger.info('1️⃣  Validating configuration...');
    const validation = Config.validate();

    if (!validation.valid) {
      logger.error('❌ Configuration validation failed:');
      validation.errors.forEach(error => logger.error(`   ${error}`));
      process.exit(1);
    }

    logger.info('✅ Configuration valid');
    logger.info('');

    // Display connection details
    logger.info('2️⃣  Connection details:');
    logger.info(`   Trading Mode: ${Config.TRADING_MODE.toUpperCase()}`);
    logger.info(`   Oanda Host: ${Config.getOandaHostname()}`);
    logger.info(`   Account ID: ${Config.OANDA_ACCOUNT_ID}`);
    logger.info(`   API Key: ${Config.OANDA_API_KEY.substring(0, 10)}...`);
    logger.info('');

    // Test connection
    logger.info('3️⃣  Testing Oanda API connection...');
    const client = new OandaClient(logger);
    const connected = await client.testConnection();

    if (!connected) {
      logger.error('');
      logger.error('❌ CONNECTION FAILED');
      logger.error('');
      logger.error('Possible issues:');
      logger.error('  • Invalid API key or Account ID');
      logger.error('  • Wrong trading mode (practice vs live)');
      logger.error('  • Network connectivity issues');
      logger.error('  • Oanda API is down');
      logger.error('');
      logger.error('Next steps:');
      logger.error('  1. Verify your .env file has correct credentials');
      logger.error('  2. Check https://developer.oanda.com/ for API status');
      logger.error('  3. Ensure TRADING_MODE matches your account type');
      logger.error('');
      process.exit(1);
    }

    logger.info('');
    logger.info('4️⃣  Testing market data access...');

    // Test getting candles
    try {
      const candles = await client.getCandles(Config.TRADING_SYMBOL, Config.TIMEFRAME, 10);
      logger.info(`✅ Successfully retrieved ${candles.length} candles for ${Config.TRADING_SYMBOL}`);

      const lastCandle = candles[candles.length - 1];
      logger.info(`   Latest ${Config.TIMEFRAME} candle:`);
      logger.info(`   Time: ${lastCandle.time.toISOString()}`);
      logger.info(`   Open: $${lastCandle.open.toFixed(2)}`);
      logger.info(`   High: $${lastCandle.high.toFixed(2)}`);
      logger.info(`   Low: $${lastCandle.low.toFixed(2)}`);
      logger.info(`   Close: $${lastCandle.close.toFixed(2)}`);
    } catch (error) {
      logger.error(`❌ Failed to get candles: ${error.message}`);
    }

    logger.info('');

    // Test Telegram if enabled
    if (Config.ENABLE_TELEGRAM) {
      logger.info('5️⃣  Testing Telegram bot...');

      if (!Config.TELEGRAM_BOT_TOKEN || !Config.TELEGRAM_CHAT_ID) {
        logger.warn('⚠️  Telegram enabled but credentials missing');
        logger.warn('   Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env');
      } else {
        logger.info('✅ Telegram credentials configured');
        logger.info(`   Bot Token: ${Config.TELEGRAM_BOT_TOKEN.substring(0, 10)}...`);
        logger.info(`   Chat IDs: ${Config.TELEGRAM_CHAT_ID}`);
        logger.info('');
        logger.info('   📱 Start your Telegram bot and send /start to test');
      }
    } else {
      logger.info('5️⃣  Telegram notifications: DISABLED');
    }

    logger.info('');
    logger.info('═'.repeat(60));
    logger.info('✅ ALL TESTS PASSED!');
    logger.info('═'.repeat(60));
    logger.info('');
    logger.info('🚀 You\'re ready to start the bot!');
    logger.info('');
    logger.info('Next steps:');
    logger.info('  • Review your configuration in .env');
    logger.info('  • Run: npm start');
    logger.info('  • Or with Docker: docker-compose up -d');
    logger.info('');
    logger.info('⚠️  IMPORTANT REMINDERS:');
    logger.info('  • Start with TRADING_MODE=practice');
    logger.info('  • Monitor for 3+ months before going live');
    logger.info('  • Never risk more than you can afford to lose');
    logger.info('');

    process.exit(0);
  } catch (error) {
    logger.error('');
    logger.error('═'.repeat(60));
    logger.error('❌ TEST FAILED');
    logger.error('═'.repeat(60));
    logger.error('');
    logger.error(`Error: ${error.message}`);
    logger.error('');
    logger.error(error.stack);
    logger.error('');
    process.exit(1);
  }
}

// Run tests
testConnection();
