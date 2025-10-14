# Security Notice

## Development vs Production Credentials

### ⚠️ Important Security Information

This project contains **DEMO CREDENTIALS** that are safe for local development and learning purposes only. These credentials are intentionally simple and publicly visible.

### Default Credentials in This Repository

The following credentials are hardcoded for ease of setup:

**PostgreSQL Database:**
- Username: `dataengineer`
- Password: `SecurePass123!`
- Database: `ecommerce`

**pgAdmin:**
- Email: `admin@ecommerce.com`
- Password: `admin123`

### 🚨 Before Production Deployment

**NEVER use these credentials in production!** Before deploying to any production environment:

1. **Use Environment Variables**
   ```bash
   # Create a .env file (already gitignored)
   DB_USER=your_prod_user
   DB_PASSWORD=your_secure_password
   KAFKA_BOOTSTRAP_SERVERS=your_kafka_cluster
   ```

2. **Use Secrets Management**
   - AWS Secrets Manager
   - HashiCorp Vault
   - Azure Key Vault
   - Kubernetes Secrets

3. **Update docker-compose.yml**
   ```yaml
   environment:
     POSTGRES_PASSWORD: ${DB_PASSWORD}  # From .env file
   ```

4. **Rotate All Credentials**
   - Generate strong, unique passwords
   - Use different credentials for each environment
   - Enable password rotation policies

5. **Enable Security Features**
   - SSL/TLS for all connections
   - Network encryption
   - Authentication tokens for Kafka
   - Database connection pooling with encryption

### Best Practices

- ✅ Use `.env` files for local development (gitignored)
- ✅ Use secret management systems for production
- ✅ Never commit real credentials to version control
- ✅ Regularly rotate passwords
- ✅ Use principle of least privilege
- ✅ Enable audit logging
- ✅ Implement network segmentation

### For This Demo Project

This is a **portfolio/learning project** intended for:
- ✅ Local development
- ✅ Educational purposes
- ✅ Demonstrating technical capabilities
- ✅ Running on localhost only

The simplified credentials make it easy to get started quickly without security overhead for a local demo.

### Reporting Security Issues

If you find a security vulnerability in this codebase, please open a GitHub issue or contact the repository owner.

---

*Remember: This is a demo project. Real-world deployments require proper security measures.*

