#pragma once

#include "CoreMinimal.h"
#include "GameFramework/PlayerController.h"
#include "WarCameraRules.h"
#include "WarActionBarRules.h"
#include "WarCombatFeedback.h"
#include "WarPlayerController.generated.h"

class UWarInterfaceWidget;
class UWarActionBarWidget;
class UWarEntryStatusWidget;
class UWarInventoryWidget;
class UWarQuestLogWidget;
class UWarWorldEditWidget;
class UWarAbilityWorkshopWidget;
class UWarCityServiceWidget;
class AWarCityNpc;
class AWarZonePortal;
class UWarFrontendWidget;
class UWarCharacterVisualDefinition;
class UWarSiegeLobbyWidget;

UCLASS()
class AEGISWAR_API AWarPlayerController : public APlayerController
{
    GENERATED_BODY()
public:
    AWarPlayerController();
    FString ScenarioCharacterId;
    UFUNCTION(Server, Reliable) void ServerPrepareScenario();
    UFUNCTION(Server, Reliable) void ServerScenarioDepart(const FString& Ticket);
    UFUNCTION(Client, Reliable) void ClientScenarioRegistered(const FString& Url,const FString& Token,const FString& Id);
    UFUNCTION(Client, Reliable) void ClientScenarioConnectionStatus(bool Pending,const FString& Message);
    UFUNCTION(Client, Reliable) void ClientScenarioTravel(const FString& Endpoint,const FString& Ticket);
    UFUNCTION(Server, Reliable) void ServerSiegeSquadOrder(int32 Round, uint8 Order);
    UFUNCTION(Client, Reliable) void ClientSiegeSquadState(uint8 Order, int32 Count);
    uint8 SiegeSquadOrder = 0;
    int32 SiegeSquadCount = 0;
    FVector SiegeHoldPosition = FVector::ZeroVector;
    void RestoreGameplayInput();
    UFUNCTION(Client, Reliable) void ClientOpenFrontend();
    UFUNCTION(Client, Reliable) void ClientCharacterEntryResult(bool bAccepted, const FString& Error);
    UFUNCTION(Server, Reliable) void ServerCreateDevelopmentCharacter(const FString& Name, FName Race, FName Career, FName Body);
    UWarCharacterVisualDefinition* GetCreatedCharacterVisual() const { return CreatedCharacterVisual; }
    bool IsCharacterEntryPending() const { return bCharacterEntryPending; }
    /** Authority lifecycle after validation; completion follows successful possession. */
    void BeginCharacterEntry(UWarCharacterVisualDefinition* Visual);
    void CompleteCharacterEntry();
    UFUNCTION(Client, Reliable) void ClientEntryRejected(const FText& Reason);
    UFUNCTION(Client, Reliable) void ClientZoneTravelStatus(const FString& Message);
    UFUNCTION(Server, Reliable) void ServerEnterPortal(AWarZonePortal* Portal);
    const FString& GetZoneTravelStatus() const { return ZoneTravelStatus; }
    void RecordEntryFailure(const FText& Reason);
    const FText& GetEntryFailure() const { return LastEntryFailure; }
    virtual void BeginPlay() override;
    virtual void SetupInputComponent() override;
    virtual void PlayerTick(float DeltaTime) override;
    void BindActionBarKeys();
    void ActivateActionSlot(int32 Slot);
    FName GetActionSlot(int32 Slot);
    bool SetActionSlot(int32 Slot, FName Action);
    FWarActionSlotView GetActionSlotView(int32 Slot);
    FString GetActionLabel(FName Action) const;
    TArray<FName> GetAvailableActions() const;
    FString GetClassAbilityStatus() const;
    void CycleCombatTarget();
    void TargetNearestEnemy();
    void SelectCombatTargetUnderCursor();
    bool SelectCombatTarget(AActor* Target);
    bool IsEnemyCombatTarget(const AActor* Target) const;
    AActor* GetCombatTarget() const;
    bool IsCombatTarget(const AActor* Target) const;
    FString GetCombatTargetLabel() const;
    FString GetActionMessage() const;
    void SendCombatNotice(FName Kind, const FString& Label, float Amount);
    UFUNCTION(Client, Unreliable) void ClientCombatNotice(uint32 Serial, FName Kind, const FString& Label, float Amount);
    const TArray<FWarCombatNotice>& GetCombatNotices() const { return CombatNotices; }
    const TArray<FWarActionBarLayout>& GetActionBars();
    int32 AddActionBar(int32 Buttons);
    void RemoveActionBar(int32 Id);
    void ResizeActionBar(int32 Id, int32 Buttons);
    void MoveActionBar(int32 Id, FVector2D Position, bool bSave);
    void SetEditingUi(bool bEditing);
    bool IsEditingUi() const { return bEditingUi; }
    bool HasActionSlot(int32 Slot);
    void SaveActionBars();
    void RebuildActionBars();
    void ToggleMenu();
    void ToggleMap();
    void ToggleCharacter();
    void ToggleGuide();
    void ToggleGmTools();
    void OpenAbilityWorkshop();
    bool CanUseGmTools() const;
    void CopyGmCoordinates();
    void MeasureWorldObject(FName Id);
    UFUNCTION(Server, Reliable) void ServerGmRestore();
    UFUNCTION(Exec) void WarSiegeStart(int32 Capacity = 6, int32 Seed = 1);
    UFUNCTION(Exec) void WarSiegeReset();
    UFUNCTION(Server, Reliable) void ServerGmSiegeStart(int32 Capacity, int32 Seed);
    UFUNCTION(Server, Reliable) void ServerGmSiegeReset();
    UFUNCTION(Server, Reliable) void ServerSiegeReady(int32 ExpectedRound, bool bReady);
    UFUNCTION(Server, Reliable) void ServerSiegeSelectRole(int32 ExpectedRound, uint8 CombatRole);
    void TickSiegeLobby();
    UFUNCTION(Server, Reliable) void ServerGmSetLevel(int32 Level);
    UFUNCTION(Server, Reliable) void ServerGmResetCooldowns();
    UFUNCTION(Server, Reliable) void ServerGmGoToCharacter(const FString& Name);
    UFUNCTION(Server, Reliable) void ServerGmTeleportZone(FName Zone);
    UFUNCTION(Server, Reliable) void ServerResetWorldDraft(int32 Revision);
    UFUNCTION(Server, Reliable) void ServerDuplicateWorldObject(FName Id, int32 Revision);
    void ShowInterface(FName Page);
    void CloseInterface();
    bool CloseAllPanels();
    bool IsInterfaceOpen() const;
    void SaveInterfacePreferences();
    FKey GetControlKey(FName Action) const;
    bool SetControlKey(FName Action, FKey Key, FString& Error);
    void ResetControlKeys();
    void LoadControlKeys();
    void BindControlKeys();
    float GetInterfaceVolume() const { return InterfaceVolume; }
    void SetInterfaceVolume(float Volume);
    float GetCombatShakeIntensity() const { return CombatShakeIntensity; }
    void SetCombatShakeIntensity(float Value);
    virtual void UpdateRotation(float DeltaTime) override;
    void ToggleInventory();
    void ToggleQuestLog();
    void ToggleWorldEditor();
    void PickWorldEditorObject();
    bool IsWorldEditorOpen() const;
    UFUNCTION(Server, Reliable) void ServerPublishWorldDraft(int32 ExpectedRevision);
    UFUNCTION(Server, Reliable) void ServerPlaceWorldObjectAtPointer(FName TemplateId, FVector Origin, FVector Direction, double Grid, double Angle, int32 ExpectedRevision);
    UFUNCTION(Server, Reliable) void ServerSetDevelopmentTraversal(bool bFlying, float SpeedMultiplier);
    UFUNCTION(Server, Reliable) void ServerReturnToDevelopmentSpawn();
    UFUNCTION(Server, Reliable) void ServerEditWorldObject(FName Id, FTransform Transform, bool bObjectHidden, int32 ExpectedRevision);
    UFUNCTION(Server, Reliable) void ServerCreateWorldObject(FName TemplateId, FTransform Transform, int32 ExpectedRevision);
    UFUNCTION(Server, Reliable) void ServerPlaceWorldObject(FName TemplateId, double Grid, double Angle, int32 ExpectedRevision);
    UFUNCTION(Server, Reliable) void ServerDropWorldObject(FName Id, int32 ExpectedRevision);
    UFUNCTION(Server, Reliable) void ServerCreateWorldRow(FName Id, int32 Count, bool bAlongY, double Gap, double Grid, int32 ExpectedRevision);
    UFUNCTION(Client, Reliable) void ClientWorldObjectCreated(FName Id);
    UFUNCTION(Server, Reliable) void ServerWorldEditHistory(bool bRedo, int32 ExpectedRevision);
    UFUNCTION(Server, Reliable) void ServerWorldEditDraft(bool bLoad, int32 ExpectedRevision);
    UFUNCTION(Client, Reliable) void ClientWorldEditResult(const FString& Message);
    const FString& GetWorldEditMessage() const { return WorldEditMessage; }
    void InteractWithStation();
    void InteractWithWorld();
    void OpenCityService(AWarCityNpc* Npc);
    void CloseCityService();
    /** No-op unless the explicitly opted-in development proof subsystem exists. */
    UFUNCTION(Server, Reliable) void ServerDevelopmentProofReady();
    UFUNCTION(Client, Reliable) void ClientDevelopmentProofStart();
    FWarCameraState& GetLocalCameraState() { return LocalCameraState; }
    void InitializeCameraYaw(double Yaw)
    {
        if (!bCameraInitialized) { LocalCameraState.Yaw = Yaw; bCameraInitialized = true; }
    }
private:
    TArray<AActor*> GetEnemyTargets() const;
    uint32 NextCombatSerial = 0, LastCombatSerial = 0;
    double CombatNoticeWindow = 0;
    int32 CombatNoticeCount = 0;
    TArray<FWarCombatNotice> CombatNotices;
    UPROPERTY(Transient) TObjectPtr<UWarSiegeLobbyWidget> SiegeLobbyWidget;
    bool bSiegeLobbyInput = false;
    UPROPERTY(Transient) TObjectPtr<UWarActionBarWidget> ActionBarWidget;
    TMap<int32, FName> ActionSlots;
    FName ActionSlotCareer;
    TArray<FWarActionBarLayout> ActionBars;
    bool bActionBarsLoaded = false;
    bool bEditingUi = false;
    int32 NextActionBarId = 1;
    TWeakObjectPtr<AActor> CombatTarget;
    FString ActionMessage;
    double ActionMessageUntil = 0;
    FString ZoneTravelStatus;
    TMap<FName,FKey> ControlKeys;
    UPROPERTY(Transient) TObjectPtr<UWarInterfaceWidget> InterfaceWidget;
    float InterfaceVolume = 1.f;
    UPROPERTY(Transient) TObjectPtr<UWarFrontendWidget> FrontendWidget;
    UPROPERTY(Transient) TObjectPtr<UWarCharacterVisualDefinition> CreatedCharacterVisual;
    bool bCharacterEntryPending = false;
    UPROPERTY(Transient) TObjectPtr<UWarInventoryWidget> InventoryWidget;
    UPROPERTY(Transient) TObjectPtr<UWarQuestLogWidget> QuestLogWidget;
    UPROPERTY(Transient) TObjectPtr<UWarWorldEditWidget> WorldEditWidget;
    UPROPERTY(Transient) TObjectPtr<UWarAbilityWorkshopWidget> AbilityWorkshopWidget;
    UPROPERTY(Transient) TObjectPtr<UWarCityServiceWidget> CityServiceWidget;
    FString WorldEditMessage;
    bool bWorldPublicationRestored = false;
    UPROPERTY(Transient) TObjectPtr<UWarEntryStatusWidget> EntryStatus;
    UPROPERTY(Transient) FText LastEntryFailure;
    // The controller survives pawn death; zoom, orbit and preferences must survive it too.
    FWarCameraState LocalCameraState;
    float CombatShakeIntensity = .25f;
    double NextImpactSound = 0;
    bool bCameraInitialized = false;
};
