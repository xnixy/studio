const { withDangerousMod } = require("expo/config-plugins");
const fs = require("fs");
const path = require("path");

const LINE = "export SENTRY_DISABLE_AUTO_UPLOAD=true";

/**
 * Local Xcode has no SENTRY_ORG. Skip source-map upload so the bundle script
 * does not fail the build. EAS already sets the same env in eas.json.
 */
function withSentryDisableAutoUpload(config) {
  return withDangerousMod(config, [
    "ios",
    async (mod) => {
      const envFile = path.join(mod.modRequest.platformProjectRoot, ".xcode.env");
      let contents = fs.existsSync(envFile) ? fs.readFileSync(envFile, "utf8") : "";
      if (!contents.includes("SENTRY_DISABLE_AUTO_UPLOAD")) {
        if (contents.length && !contents.endsWith("\n")) contents += "\n";
        contents += `${LINE}\n`;
        fs.writeFileSync(envFile, contents);
      }
      return mod;
    },
  ]);
}

module.exports = withSentryDisableAutoUpload;
