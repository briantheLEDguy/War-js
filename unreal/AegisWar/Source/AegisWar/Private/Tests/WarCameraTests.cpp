#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarCameraRules.h"
#include "EnhancedInputSubsystemInterface.h"
#include "Engine/World.h"
#include "GameFramework/InputSettings.h"
#include "GameFramework/PlayerController.h"
#include "InputAction.h"
#include "InputKeyEventArgs.h"
#include "InputMappingContext.h"
#include "Misc/ScopeExit.h"
#include <limits>

namespace
{
    // Exercise the engine's mapping rebuild, including imported legacy axis modifiers.
    class FCameraInputSubsystem final : public IEnhancedInputSubsystemInterface
    {
    public:
        explicit FCameraInputSubsystem(UEnhancedPlayerInput* InInput) : Input(InInput) {}
        virtual UEnhancedPlayerInput* GetPlayerInput() const override { return Input; }
    protected:
        virtual TMap<TObjectPtr<const UInputAction>, FInjectedInput>& GetContinuouslyInjectedInputs() override { return InjectedInputs; }
    private:
        UEnhancedPlayerInput* Input;
        TMap<TObjectPtr<const UInputAction>, FInjectedInput> InjectedInputs;
    };
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarCameraTest, "AegisWar.Foundation.CameraControls",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FWarCameraTest::RunTest(const FString& Parameters)
{
    FWarCameraState Camera;
    TestEqual(TEXT("Seven metre outdoor default"), Camera.Distance, 700.0);
    Camera.WheelPixels(-10000); TestEqual(TEXT("Outdoor near limit"), Camera.Distance, 300.0);
    Camera.WheelPixels(10000); TestEqual(TEXT("Outdoor far limit"), Camera.Distance, 1400.0);
    Camera.WheelPixels(-500); Camera.OrbitPixels(100, 25);
    const double Distance = Camera.Distance, Yaw = Camera.Yaw, Pitch = Camera.Pitch;
    Camera.SetIndoor(true);
    TestEqual(TEXT("Indoor entry distance"), Camera.Distance, 220.0);
    TestEqual(TEXT("Indoor yaw reset"), Camera.Yaw, 0.0);
    TestTrue(TEXT("Indoor pitch reset"), FMath::IsNearlyEqual(Camera.Pitch, -FMath::RadiansToDegrees(0.42)));
    Camera.WheelPixels(-10000); TestEqual(TEXT("Indoor near limit"), Camera.Distance, 165.0);
    Camera.WheelPixels(10000); TestEqual(TEXT("Indoor far limit"), Camera.Distance, 380.0);
    Camera.SetIndoor(true); TestEqual(TEXT("Repeated entry is idempotent"), Camera.Distance, 380.0);
    Camera.OrbitPixels(70, -50); Camera.SetIndoor(false);
    TestEqual(TEXT("Outdoor zoom restored"), Camera.Distance, Distance);
    TestEqual(TEXT("Outdoor yaw restored"), Camera.Yaw, Yaw);
    TestEqual(TEXT("Outdoor pitch restored"), Camera.Pitch, Pitch);
    Camera.SetIndoor(false); TestEqual(TEXT("Repeated exit is idempotent"), Camera.Yaw, Yaw);
    FWarCameraState Normal, Inverted;
    Inverted.SetPreferences(1, 1, true, true);
    Normal.OrbitPixels(100, 20); Inverted.OrbitPixels(100, 20);
    TestTrue(TEXT("Horizontal inversion"), FMath::IsNearlyEqual(Normal.Yaw, -Inverted.Yaw));
    TestTrue(TEXT("Vertical inversion"), FMath::IsNearlyEqual(Normal.Pitch + Inverted.Pitch, -2.0 * FMath::RadiansToDegrees(0.45)));
    Camera.OrbitPixels(0, 10000);
    const double Limit = FMath::RadiansToDegrees(PI / 2.0 - 0.01);
    TestTrue(TEXT("Pitch upper limit"), FMath::IsNearlyEqual(Camera.Pitch, Limit));
    Camera.OrbitPixels(0, -10000); TestTrue(TEXT("Pitch lower limit"), FMath::IsNearlyEqual(Camera.Pitch, -Limit));
    Camera.SetPreferences(100, -1, false, false);
    TestEqual(TEXT("Look preference clamped"), Camera.LookSensitivity, 3.0);
    TestEqual(TEXT("Zoom preference clamped"), Camera.ZoomSensitivity, 0.25);
    Camera.WheelPixels(100); TestEqual(TEXT("Zoom sensitivity applied"), Camera.Distance, Distance + 25.0);
    const auto Saved = Camera;
    Camera.WheelPixels(std::numeric_limits<double>::infinity());
    Camera.OrbitPixels(std::numeric_limits<double>::quiet_NaN(), 10);
    TestEqual(TEXT("Invalid wheel leaves zoom intact"), Camera.Distance, Saved.Distance);
    TestEqual(TEXT("Invalid orbit leaves yaw intact"), Camera.Yaw, Saved.Yaw);
    TestEqual(TEXT("Invalid orbit leaves pitch intact"), Camera.Pitch, Saved.Pitch);
    Camera.SetPreferences(std::numeric_limits<double>::quiet_NaN(), std::numeric_limits<double>::infinity(), false, false);
    TestEqual(TEXT("Invalid look uses default"), Camera.LookSensitivity, 1.0);
    TestEqual(TEXT("Invalid zoom uses default"), Camera.ZoomSensitivity, 1.0);

    const auto* Settings = GetDefault<UInputSettings>();
    for (const auto Key : {EKeys::MouseX, EKeys::MouseY, EKeys::Mouse2D})
    {
        const auto* Config = Settings->AxisConfig.FindByPredicate([Key](const auto& Entry) { return Entry.AxisKeyName == Key.GetFName(); });
        if (!TestNotNull(TEXT("Merged mouse axis configuration exists"), Config)) return false;
        TestEqual(TEXT("Mouse axis preserves pixel magnitude"), Config->AxisProperties.Sensitivity, 1.f);
        TestEqual(TEXT("Mouse axis has no pixel dead zone"), Config->AxisProperties.DeadZone, 0.f);
        TestEqual(TEXT("Mouse axis has no response curve"), Config->AxisProperties.Exponent, 1.f);
        TestFalse(TEXT("Inversion belongs to the camera preference"), Config->AxisProperties.bInvert);
    }

    const auto Values = UWorld::InitializationValues().AllowAudioPlayback(false).RequiresHitProxies(false)
        .CreatePhysicsScene(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    auto* World = UWorld::CreateWorld(EWorldType::Editor, false, NAME_None, nullptr, true, ERHIFeatureLevel::Num, &Values);
    if (!TestNotNull(TEXT("Mouse input test world"), World)) return false;
    ON_SCOPE_EXIT { World->DestroyWorld(false); };
    auto* Controller = World->SpawnActor<APlayerController>();
    if (!TestNotNull(TEXT("Mouse input test controller"), Controller)) return false;
    auto* Input = NewObject<UEnhancedPlayerInput>(Controller);
    Controller->PlayerInput = Input;
    for (const auto Key : {EKeys::MouseX, EKeys::MouseY})
    {
        FInputAxisProperties Properties;
        TestTrue(TEXT("Fresh player input loads the mouse axis settings"), Input->GetAxisProperties(Key, Properties));
        TestEqual(TEXT("Fresh player input keeps physical pixel magnitude"), Properties.Sensitivity, 1.f);
    }
    FCameraInputSubsystem Subsystem(Input);
    auto* Mapping = NewObject<UInputMappingContext>(Controller);
    auto* YawAction = NewObject<UInputAction>(Mapping);
    auto* PitchAction = NewObject<UInputAction>(Mapping);
    YawAction->ValueType = PitchAction->ValueType = EInputActionValueType::Axis1D;
    Mapping->MapKey(YawAction, EKeys::MouseX);
    Mapping->MapKey(PitchAction, EKeys::MouseY);
    FModifyContextOptions Options;
    Options.bForceImmediately = true;
    Subsystem.AddMappingContext(Mapping, 0, Options);

    for (const float DeltaTime : {1.f / 30, 1.f / 60, 1.f / 120})
    {
        auto Horizontal = FInputKeyEventArgs::CreateSimulated(EKeys::MouseX, IE_Axis, 64.f);
        auto Vertical = FInputKeyEventArgs::CreateSimulated(EKeys::MouseY, IE_Axis, 32.f);
        Horizontal.DeltaTime = Vertical.DeltaTime = DeltaTime;
        Input->InputKey(Horizontal);
        Input->InputKey(Vertical);
        Input->ProcessInputStack({}, DeltaTime, false);
        const double X = Input->GetActionValue(YawAction).Get<float>(), Y = Input->GetActionValue(PitchAction).Get<float>();
        TestEqual(TEXT("Enhanced MouseX preserves physical pixel delta at every frame rate"), X, 64.0);
        TestEqual(TEXT("Enhanced MouseY preserves physical pixel delta at every frame rate"), Y, 32.0);
        FWarCameraState MouseCamera;
        const double InitialPitch = MouseCamera.Pitch;
        MouseCamera.OrbitPixels(X, -Y);
        TestTrue(TEXT("Mouse pixels receive the angular sensitivity once"), FMath::IsNearlyEqual(MouseCamera.Yaw, FMath::RadiansToDegrees(.32)));
        TestTrue(TEXT("Upward mouse movement lowers pitch at the native adapter"), FMath::IsNearlyEqual(MouseCamera.Pitch, InitialPitch - FMath::RadiansToDegrees(.096)));
        FWarCameraState Faster;
        Faster.SetPreferences(2, 1, false, false);
        Faster.OrbitPixels(X, 0);
        TestTrue(TEXT("Saved look preference scales the physical delta once"), FMath::IsNearlyEqual(Faster.Yaw, 2 * MouseCamera.Yaw));
    }
    return true;
}
#endif
