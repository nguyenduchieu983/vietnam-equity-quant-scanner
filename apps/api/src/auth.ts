import { Body, CanActivate, Controller, ExecutionContext, Injectable, Post, UnauthorizedException } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import { IsString, MaxLength, MinLength } from 'class-validator';
import { scryptSync, timingSafeEqual } from 'node:crypto';
import { required } from './config';

export class LoginDto {
  @IsString() @MinLength(12) @MaxLength(128) password!: string;
}
@Injectable()
export class AuthGuard implements CanActivate {
  constructor(private readonly jwt: JwtService) {}
  async canActivate(context: ExecutionContext) {
    const req = context.switchToHttp().getRequest();
    const token = req.headers.authorization?.match(/^Bearer ([^\s]+)$/)?.[1];
    try {
      const claims = await this.jwt.verifyAsync(token ?? '');
      if (claims.sub !== 'admin') throw new Error('invalid subject');
      req.user = claims;
      return true;
    } catch { throw new UnauthorizedException('Authentication required'); }
  }
}
@Controller('auth')
export class AuthController {
  constructor(private readonly jwt: JwtService) {}
  @Post('login')
  async login(@Body() body: LoginDto) {
    const actual = scryptSync(body.password, required('ADMIN_PASSWORD_SALT'), 64);
    const expected = Buffer.from(required('ADMIN_PASSWORD_HASH'), 'hex');
    if (actual.length !== expected.length || !timingSafeEqual(actual, expected)) throw new UnauthorizedException('Invalid credentials');
    return { accessToken: await this.jwt.signAsync({ sub: 'admin' }), expiresIn: 1800 };
  }
}
