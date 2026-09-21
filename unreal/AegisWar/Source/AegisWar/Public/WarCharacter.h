#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "AbilitySystemInterface.h"
#include "WarCameraRules.h"
#include "WarMovementInput.h"
#include "WarCharacter.generated.h"

class UWarCharacterVisualDefinition;
class USpringArmComponent;
class UCameraComponent;
class UInputAction;
class UInputMappingContext;
class UEnhancedInputLocalPlayerSubsystem;
struct FInputActionValue;

UCLASS()
class AEGISWAR_API AWarCharacter : public ACharacter, public IAbilitySystemInterface
{
    GENERATED_BODY()
public:
    AWarCharacter();
    virtual UAbilitySystemComponent* GetAbilitySystemComponent() const override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    virtual void PossessedBy(AController* NewController) override;
    virtual void OnRep_PlayerState() override;
    virtual void SetupPlayerInputComponent(UInputComponent* PlayerInputComponent) override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
    virtual void Tick(float DeltaSeconds) override;

    bool SetVisualDefinition(UWarCharacterVisualDefinition* Definition, FString& OutError);
    bool IsDead() const { return bDead; }
    bool IsVisualReady() const { return bVisualReady; }
    FName GetPlayingAnimation() const { return PlayingAnimation; }
    bool CanStrikeTarget(const AWarCharacter* Target) const;
    AWarCharacter* GetRequestedStrikeTarget() const { return RequestedStrikeTarget.Get(); }
    void HandleDeath();
    /** The server revalidates target, range, realm, cost and cooldown for every request. */
    UFUNCTION(BlueprintCallable, Category="Combat") void RequestTargetStrike(AWarCharacter* Target);
    UFUNCTION(NetMulticast, Unreliable) void MulticastPlayStrike();
    void ApplyCameraOrbit(double X, double Y);
    void ApplyCameraWheel(double DeltaPixels);
    UFUNCTION(BlueprintCallable, Category="Camera") void SetCameraIndoorMode(bool bEnabled);
    UFUNCTION(BlueprintCallable, Category="Camera") void SetCameraPreferences(float LookSensitivity, float ZoomSensitivity, bool bInvertX, bool bInvertY);
    double GetCameraDistance() const;
    UFUNCTION(BlueprintCallable, Category="Movement") void ToggleAutoRun();
    bool IsAutoRunning() const { return MovementInput.bAutoRun; }
    bool SetDevelopmentTraversal(bool bFlying, float SpeedMultiplier, FString& Error);
    bool ReturnToDevelopmentSpawn(FString& Error);
    bool IsDevelopmentFlying() const { return bDevelopmentFlying && !bDead; }
    float GetDevelopmentSpeed() const { return DevelopmentSpeed; }

protected:
    UPROPERTY(VisibleAnywhere, Category="Camera") TObjectPtr<USpringArmComponent> CameraBoom;
    UPROPERTY(VisibleAnywhere, Category="Camera") TObjectPtr<UCameraComponent> FollowCamera;
    UPROPERTY(ReplicatedUsing=OnRep_VisualDefinition) TObjectPtr<UWarCharacterVisualDefinition> VisualDefinition;
    UPROPERTY(ReplicatedUsing=OnRep_Dead) bool bDead = false;

private:
    UFUNCTION() void OnRep_VisualDefinition();
    UFUNCTION() void OnRep_Dead();
    UFUNCTION(Server, Reliable) void ServerRequestStrike(AWarCharacter* Target);
    bool ApplyVisual(FString& OutError);
    void PlayImportedAnimation(FName Name, bool bLoop);
    void InitializeAbilityActor();
    void MoveForward(const FInputActionValue& Value);
    void MoveRight(const FInputActionValue& Value);
    void LookYaw(const FInputActionValue& Value);
    void LookPitch(const FInputActionValue& Value);
    void Zoom(const FInputActionValue& Value);
    void UpdateCamera();
    bool CanControlCamera() const;
    FWarCameraState* GetCameraState() const;
    void StartJump();
    void UpdateMovementInput();
    void RequestStrike();

    UPROPERTY(Transient) TObjectPtr<UInputMappingContext> MappingContext;
    UPROPERTY(Transient) TObjectPtr<UInputAction> MoveForwardAction;
    UPROPERTY(Transient) TObjectPtr<UInputAction> MoveRightAction;
    UPROPERTY(Transient) TObjectPtr<UInputAction> LookYawAction;
    UPROPERTY(Transient) TObjectPtr<UInputAction> LookPitchAction;
    UPROPERTY(Transient) TObjectPtr<UInputAction> ZoomAction;
    UPROPERTY(Transient) TObjectPtr<UInputAction> JumpAction;
    UPROPERTY(Transient) TObjectPtr<UInputAction> StrikeAction;
    UPROPERTY(Transient) TObjectPtr<UInputAction> AutoRunAction;
    FWarMovementInput MovementInput;
    double ForwardAxis = 0.0, RightAxis = 0.0;
    TWeakObjectPtr<AWarCharacter> RequestedStrikeTarget;
    TWeakObjectPtr<UEnhancedInputLocalPlayerSubsystem> InputSubsystem;
    double NextStrikeRequestTime = 0.0;
    bool bVisualReady = false;
    FName PlayingAnimation;
    double ActionAnimationUntil = 0.0;
    bool bDevelopmentFlying = false, bDevelopmentSpeedsCaptured = false;
    float DevelopmentSpeed = 1.f, DevelopmentBaseWalkSpeed = 600.f, DevelopmentBaseFlySpeed = 600.f;
    float DevelopmentBaseBraking = 0.f;
    ECollisionEnabled::Type DevelopmentCollision = ECollisionEnabled::QueryAndPhysics;
};
