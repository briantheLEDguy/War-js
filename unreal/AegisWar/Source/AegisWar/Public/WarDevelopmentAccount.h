#pragma once
#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "WarDevelopmentAccount.generated.h"

/** Development-only credentials remain in memory and are never replicated. */
UCLASS()
class AEGISWAR_API UWarDevelopmentAccount : public UGameInstanceSubsystem
{
    GENERATED_BODY()
public:
    virtual void Deinitialize() override;
    void BeginLogin();
    void Logout();
    FString GetStatus() const { return Status; }
    bool IsApproved() const { return bApproved; }
    static bool IsAllowedLoginUrl(const FString& Url);
    /** Credentials remain private; only bounded authenticated gateway requests leave this subsystem. */
    void GatewayRequest(const FString& Method,const FString& Path,const FString& Body,TFunction<void(int32,const FString&)> Complete);
private:
    void PollLogin();
    void VerifyGateway();
    FString LocalKey, AccessToken, Status = TEXT("Not signed in for development.");
    FString AccountId;
    bool bApproved = false;
    bool bPolling = false;
    uint64 LoginGeneration = 0;
    double Deadline = 0;
    FTimerHandle LoginTimer;
};
