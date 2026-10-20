import 'reflect-metadata';
import 'dotenv/config';
import { NestFactory } from '@nestjs/core';
import { ArgumentsHost, Catch, ExceptionFilter, HttpException, ValidationPipe } from '@nestjs/common';
import { DocumentBuilder, SwaggerModule } from '@nestjs/swagger';
import helmet from 'helmet';
import { randomUUID } from 'node:crypto';
import { map } from 'rxjs';
import { AppModule } from './app';
import { mode } from './config';

@Catch()
class ErrorFilter implements ExceptionFilter {
  catch(error: unknown, host: ArgumentsHost) {
    const ctx = host.switchToHttp();
    const code = error instanceof HttpException ? error.getStatus() : 500;
    const req = ctx.getRequest();
    const message = error instanceof HttpException ? error.message : 'Internal service error';
    ctx.getResponse().status(code).json({
      data: null, meta: { asOf: null, source: mode() === 'demo' ? 'fixture' : 'unavailable', isDemo: mode() === 'demo', runId: null, freshness: 'UNKNOWN' },
      error: { code: `HTTP_${code}`, message, requestId: req.requestId }
    });
  }
}
async function bootstrap() {
  mode();
  const app = await NestFactory.create(AppModule);
  app.use(helmet());
  app.use((req: any, res: any, next: () => void) => {
    req.requestId = randomUUID();
    res.setHeader('X-Request-ID', req.requestId);
    res.on('finish', () => console.log(JSON.stringify({ requestId: req.requestId, method: req.method, path: req.path, status: res.statusCode })));
    next();
  });
  app.setGlobalPrefix('api/v1');
  app.useGlobalPipes(new ValidationPipe({ whitelist: true, forbidNonWhitelisted: true, transform: true }));
  app.useGlobalFilters(new ErrorFilter());
  app.useGlobalInterceptors({ intercept: (_ctx, next) => next.handle().pipe(map(data => ({
    data, meta: { asOf: data?.latestSession ?? null, source: mode() === 'demo' ? 'fixture' : 'unavailable', isDemo: mode() === 'demo', runId: null, freshness: mode() === 'demo' ? 'DEMO' : 'DATA_UNAVAILABLE' }, error: null
  }))) });
  if (process.env.NODE_ENV !== 'production') {
    SwaggerModule.setup('api/docs', app, SwaggerModule.createDocument(app, new DocumentBuilder().setTitle('Quant VN • M0').setVersion('0.1.0').addBearerAuth().build()));
  }
  app.enableShutdownHooks();
  await app.listen(Number(process.env.PORT ?? 3000), '127.0.0.1');
}
void bootstrap();
