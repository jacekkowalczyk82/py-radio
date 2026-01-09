import boto3
import os
import configparser

def test_permissions():
    print("--- Verifying AWS Polly Permissions ---")
    
    # 1. Load Config to simulate app behavior
    config_path = os.path.expanduser("~/.config/py-radio/config.ini")
    print(f"Reading config from: {config_path}")
    
    config = configparser.ConfigParser()
    config.read(config_path)
    
    profile_name = "default"
    region_name = "us-east-2"
    
    if "aws" in config.sections():
        if "radio.aws.profile" in config["aws"]:
            profile_name = config["aws"]["radio.aws.profile"]
        if "radio.aws.region" in config["aws"]:
             region_name = config["aws"]["radio.aws.region"]

    print(f"Configured Profile: {profile_name}")
    print(f"Configured Region: {region_name}")

    try:
        # 2. Create Session
        if profile_name != "default":
            session = boto3.Session(profile_name=profile_name, region_name=region_name)
        else:
            session = boto3.Session(region_name=region_name)
            
        print("Session created.")
        
        # 3. Check Identity
        sts = session.client("sts")
        identity = sts.get_caller_identity()
        print(f"Current Identity ARN: {identity['Arn']}")
        print(f"Current Account: {identity['Account']}")
        
        # 4. Test Polly
        print("\nAttempting to call polly:SynthesizeSpeech...")
        polly = session.client("polly")
        response = polly.synthesize_speech(
            Text="Test permission check.",
            OutputFormat="mp3",
            VoiceId="Maja"
        )
        print("SUCCESS! Polly generated audio stream.")
        
    except Exception as e:
        print("\n!!! FAILED !!!")
        print(f"Error: {e}")

if __name__ == "__main__":
    test_permissions()
